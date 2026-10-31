from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import AnswerStatus, CandidateAnswer, CandidateClaim, EvidenceRecord, RetrievalResult, VerificationReport, VerifiedClaim, VerifiedSource


_STOPWORDS = {"a", "an", "and", "are", "because", "for", "from", "how", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "what", "why", "with"}
_CONFLICT_MARKERS = ("conflict", "contradict", "disagree", "unresolved")


def verify_answer(candidate: CandidateAnswer, retrieval: RetrievalResult, evidence: list[EvidenceRecord]) -> tuple[str, VerificationReport]:
    """Mechanically verify citations and conservatively assess textual support.

    This does not prove that a source's historical rationale is true; it only checks
    citation integrity and applies a transparent lexical support heuristic.
    """
    evidence_by_id = {item.evidence_id: item for item in evidence}
    retrieved_ids = {hit.evidence_id for hit in retrieval.hits}
    available_ids = retrieved_ids & set(evidence_by_id)
    warnings = list(retrieval.warnings)
    unknown_ids = (set(candidate.evidence_ids) | {citation for claim in candidate.claims for citation in claim.evidence_ids}) - available_ids
    if unknown_ids:
        warnings.append("citation_not_found_in_retrieved_evidence")

    claims = candidate.claims or [CandidateClaim(text=candidate.answer, evidence_ids=candidate.evidence_ids)]
    verified_claims: list[VerifiedClaim] = []
    for claim in claims:
        ids = list(dict.fromkeys(claim.evidence_ids))
        valid_ids = [evidence_id for evidence_id in ids if evidence_id in available_ids]
        claim_warnings: list[str] = []
        if set(ids) - available_ids:
            claim_warnings.append("claim_cites_missing_evidence")
            support = "unsupported"
        elif not valid_ids:
            claim_warnings.append("claim_has_no_evidence_link")
            support = "unsupported"
        else:
            support = _support_level(claim.text, [evidence_by_id[evidence_id] for evidence_id in valid_ids])
            if support != "supported":
                claim_warnings.append("semantic_support_requires_review")
        verified_claims.append(VerifiedClaim(text=claim.text, evidence_ids=valid_ids, support=support, warnings=claim_warnings))

    cited_ids = sorted({evidence_id for claim in verified_claims for evidence_id in claim.evidence_ids})
    sources: list[VerifiedSource] = []
    for evidence_id in cited_ids:
        item = evidence_by_id[evidence_id]
        source_url = _trusted_url(item.source_url)
        if item.source_url and source_url is None:
            warnings.append("invalid_stored_source_url_omitted")
        sources.append(VerifiedSource(evidence_id=evidence_id, source_type=item.source_type, title=item.title, source_url=source_url, observed_at=item.observed_at))

    if not retrieval.hits:
        status: AnswerStatus = "insufficient_evidence"
        warnings.append("no_retrieved_evidence")
    elif unknown_ids or any(claim.support == "unsupported" for claim in verified_claims) or (verified_claims and all(claim.support == "uncertain" for claim in verified_claims)):
        status = "insufficient_evidence"
    elif retrieval.status == "conflicting" or candidate.conflicts or any(claim.support == "conflicting" or _contains_conflict(claim.text) for claim in verified_claims):
        status = "conflicting_evidence"
        warnings.append("retrieved_or_declared_conflicting_evidence")
    elif candidate.status == "insufficient_evidence":
        status = "insufficient_evidence"
    elif any(claim.support == "uncertain" for claim in verified_claims):
        status = "partially_supported"
    else:
        status = "supported"

    if not candidate.claims and candidate.status in {"supported", "partially_supported"}:
        warnings.append("claim_support_requires_semantic_review")
        if status == "supported":
            status = "partially_supported"
    if status == "insufficient_evidence":
        answer = "I cannot establish this from the retrieved evidence. The available sources do not support a reliable explanation."
    elif status == "conflicting_evidence":
        answer = "The retrieved evidence conflicts or has unresolved history, so I cannot present one explanation as established."
    elif status == "partially_supported":
        answer = f"The available evidence only partially supports this explanation: {candidate.answer}"
    else:
        answer = candidate.answer
    report = VerificationReport(status=status, claims=verified_claims, cited_evidence_ids=cited_ids, sources=sources, warnings=sorted(set(warnings)), uncertainties=[warning for warning in warnings if "review" in warning or "conflict" in warning or "missing" in warning], mechanically_verified=True)
    return answer, report


def _support_level(claim: str, evidence: list[EvidenceRecord]) -> str:
    claim_terms = _terms(claim)
    if not claim_terms:
        return "uncertain"
    best_overlap = 0.0
    conflict = False
    for item in evidence:
        text = " ".join(filter(None, [item.title, item.summary, item.excerpt])).lower()
        source_terms = _terms(text)
        best_overlap = max(best_overlap, len(claim_terms & source_terms) / len(claim_terms))
        conflict = conflict or _contains_conflict(text)
    if conflict:
        return "conflicting"
    if best_overlap >= 0.6:
        return "supported"
    return "uncertain"


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9_./-]{3,}", value.lower()) if term not in _STOPWORDS}


def _contains_conflict(value: str) -> bool:
    lower = value.lower()
    return any(marker in lower for marker in _CONFLICT_MARKERS)


def _trusted_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return None
    return value
