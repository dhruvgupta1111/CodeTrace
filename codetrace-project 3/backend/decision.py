from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from .models import DecisionCandidate, EvidenceRecord, SupersessionAssessment


_CONFIG = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
_PATH = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_-]+)?")
_REPLACEMENT = re.compile(r"\b(revert(?:s|ed)?|rollback|roll back|replace(?:s|d)?|supersed(?:e|es|ed)|restore|undo|instead of|no longer|deprecated|switch from)\b", re.I)
_DECISION = re.compile(r"\b(introduce|add(?:s|ed)?|set|make configurable|change(?:d|s)?|use|remove(?:d|s)?|disable|enable|because|due to|to avoid|to prevent|incident|adr[- ]?\d+)\b", re.I)
_CONFLICT = re.compile(r"\b(conflict(?:s|ed)?|contradict(?:s|ed|ion)?|disagree(?:s|d)?|unresolved)\b", re.I)


def stable_decision_id(repository_id: str, evidence_id: str) -> str:
    return "decision_" + hashlib.sha256(f"{repository_id}\x1f{evidence_id}".encode()).hexdigest()[:32]


def stable_assessment_id(repository_id: str, newer_id: str, older_id: str) -> str:
    return "supersession_" + hashlib.sha256(f"{repository_id}\x1f{newer_id}\x1f{older_id}".encode()).hexdigest()[:32]


def extract_decisions(repository_id: str, records: list[EvidenceRecord]) -> tuple[list[DecisionCandidate], list[SupersessionAssessment], list[str]]:
    decisions: list[DecisionCandidate] = []
    warnings: list[str] = []
    for record in records:
        text = " ".join(filter(None, [record.title, record.summary, record.excerpt]))
        if not _is_decision_candidate(record, text):
            continue
        paths = sorted({change.path for change in record.changed_files} | set(_PATH.findall(text)))
        keys = sorted(set(_CONFIG.findall(text)))
        explicit = bool(_DECISION.search(text) or record.source_type in {"decision_record", "documentation"})
        causal_support = bool(re.search(r"\b(because|due to|to avoid|to prevent|incident|adr[- ]?\d+|instead of|revert|replace|supersed|rollback)\b", text, re.I))
        status = "conflicting" if _CONFLICT.search(text) else ("confirmed" if explicit and causal_support else "unresolved")
        statement = (record.title or record.summary or record.excerpt or "").strip()[:500]
        decisions.append(DecisionCandidate(decision_id=stable_decision_id(repository_id, record.evidence_id), repository_id=repository_id, statement=statement, status=status, evidence_kind="explicit" if explicit else "inferred", evidence_ids=[record.evidence_id], affected_paths=paths, configuration_keys=keys, observed_at=record.observed_at, source_type=record.source_type, source_id=record.source_id))
    decisions.sort(key=lambda decision: (decision.observed_at is None, decision.observed_at or datetime.max.replace(tzinfo=timezone.utc), decision.decision_id))
    supersessions = _assess_supersessions(repository_id, decisions, records)
    if any(decision.observed_at is None for decision in decisions):
        warnings.append("decision_missing_timestamp")
    return decisions, supersessions, warnings


def _is_decision_candidate(record: EvidenceRecord, text: str) -> bool:
    if not text.strip():
        return False
    if record.source_type == "commit" and not (_DECISION.search(text) or _REPLACEMENT.search(text)):
        return False
    return bool(_DECISION.search(text) or _REPLACEMENT.search(text) or record.source_type in {"pull_request", "issue", "discussion", "documentation", "incident", "decision_record"})


def _assess_supersessions(repository_id: str, decisions: list[DecisionCandidate], records: list[EvidenceRecord]) -> list[SupersessionAssessment]:
    by_evidence = {record.evidence_id: record for record in records}
    assessments: list[SupersessionAssessment] = []
    for older in decisions:
        for newer in decisions:
            if older.decision_id == newer.decision_id:
                continue
            same_behavior = bool(set(older.affected_paths) & set(newer.affected_paths) or set(older.configuration_keys) & set(newer.configuration_keys))
            if not same_behavior:
                continue
            newer_record = by_evidence.get(newer.evidence_ids[0])
            newer_text = " ".join(filter(None, [newer_record.title, newer_record.summary, newer_record.excerpt])) if newer_record else newer.statement
            explicit_replacement = bool(_REPLACEMENT.search(newer_text))
            ordered = bool(older.observed_at and newer.observed_at and newer.observed_at > older.observed_at)
            if not explicit_replacement:
                continue
            if ordered and older.status != "conflicting" and newer.status != "conflicting":
                status = "confirmed"
                rationale = "Later evidence explicitly signals replacement or reversal of the same affected behavior."
            else:
                status = "uncertain"
                rationale = "Replacement language exists, but chronological order or source consistency is incomplete."
            evidence_ids = sorted(set(older.evidence_ids + newer.evidence_ids))
            assessments.append(SupersessionAssessment(assessment_id=stable_assessment_id(repository_id, newer.decision_id, older.decision_id), repository_id=repository_id, newer_decision_id=newer.decision_id, older_decision_id=older.decision_id, status=status, evidence_ids=evidence_ids, rationale=rationale, same_behavior=True))
    return assessments
