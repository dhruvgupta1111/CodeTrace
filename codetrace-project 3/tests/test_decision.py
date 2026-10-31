from __future__ import annotations

from datetime import datetime, timezone

from backend.decision import extract_decisions
from backend.evidence import normalize_commit, normalize_github_source
from backend.graph import graph_from_evidence
from backend.models import GitCommit, GitHubSource


def commit(source_id: str, message: str, date: datetime | None, path: str = "src/config.py"):
    return normalize_commit("repo_1", GitCommit(source_id=source_id, sha=source_id, message=message, author_name="A", authored_at=date, changed_paths=[path], source_url=f"https://github.com/a/b/commit/{source_id}"))[0]


def test_explicit_reversal_confirms_supersession_for_same_behavior() -> None:
    older = commit("git:old", "Set TIMEOUT_SECONDS to 30 because gateway is slow", datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = commit("git:new", "Revert timeout policy to restore previous behavior", datetime(2026, 1, 2, tzinfo=timezone.utc))
    decisions, supersessions, warnings = extract_decisions("repo_1", [older, newer])
    assert not warnings
    assert len(decisions) == 2
    assert any(item.status == "confirmed" and item.evidence_kind == "explicit" for item in decisions)
    assert len(supersessions) == 1
    assert supersessions[0].status == "confirmed"
    assert set(supersessions[0].evidence_ids) == {older.evidence_id, newer.evidence_id}

    graph = graph_from_evidence("repo_1", [older, newer], decisions=decisions, supersession_assessments=supersessions)
    assert any(edge.relationship_type == "SUPERSEDES" and edge.evidence_ids for edge in graph.edges)


def test_unrelated_newer_commit_does_not_supersede() -> None:
    older = commit("git:old", "Set TIMEOUT_SECONDS to 30 because gateway is slow", datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = commit("git:new", "Refactor logging module", datetime(2026, 1, 2, tzinfo=timezone.utc), "src/logging.py")
    _, supersessions, _ = extract_decisions("repo_1", [older, newer])
    assert supersessions == []


def test_ambiguous_change_is_unresolved_and_missing_timestamp_is_uncertain() -> None:
    older = commit("git:old", "Set TIMEOUT_SECONDS to 30", None)
    newer = commit("git:new", "Revert timeout setting", None)
    decisions, supersessions, warnings = extract_decisions("repo_1", [older, newer])
    assert any(item.status == "unresolved" for item in decisions)
    assert "decision_missing_timestamp" in warnings
    assert len(supersessions) == 1
    assert supersessions[0].status == "uncertain"


def test_conflicting_sources_remain_conflicting_and_unsupported_causal_claim_is_not_created() -> None:
    conflict = normalize_github_source("repo_1", GitHubSource(source_id="github:a/b:issue:1", source_type="issue", title="Conflicting timeout rationale", body="The discussion contradicts the earlier timeout explanation.", source_url="https://github.com/a/b/issues/1"))[0]
    unsupported = commit("git:fix", "fix retry", datetime(2026, 1, 3, tzinfo=timezone.utc), "src/retry.py")
    decisions, supersessions, _ = extract_decisions("repo_1", [conflict, unsupported])
    assert any(item.status == "conflicting" for item in decisions)
    assert not any(item.source_id == unsupported.source_id for item in decisions)
    assert supersessions == []
