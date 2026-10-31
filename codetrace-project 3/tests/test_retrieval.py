from __future__ import annotations

from datetime import datetime, timezone

from backend.evidence import normalize_commit, normalize_github_source
from backend.graph import GraphService, InMemoryGraphStore, graph_from_evidence
from backend.models import GitCommit, GitHubSource
from backend.retrieval import RetrievalService, understand_question
from backend.store import Store


def make_records(repository_id: str = "repo_1"):
    commit, _ = normalize_commit(repository_id, GitCommit(
        source_id="git:retry", sha="retry", message="Add retry policy", author_name="A", authored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        changed_paths=["src/retry_policy.py"], source_url="https://github.com/a/b/commit/retry",
    ))
    issue, _ = normalize_github_source(repository_id, GitHubSource(
        source_id="github:a/b:issue:9", source_type="issue", title="Gateway context", body="The gateway rate limit required bounded retries in src/retry_policy.py.", source_url="https://github.com/a/b/issues/9",
    ))
    irrelevant, _ = normalize_github_source(repository_id, GitHubSource(
        source_id="github:a/b:issue:10", source_type="issue", title="Unrelated UI", body="Update the button color.", source_url="https://github.com/a/b/issues/10",
    ))
    return [commit, issue, irrelevant]


def service(tmp_path, use_graph=True):
    store = Store(tmp_path / "state.sqlite3")
    store.upsert_repository({"id": "repo_1", "full_name": "a/b", "remote_url": "https://github.com/a/b.git", "default_branch": "main", "index_status": "indexed", "last_indexed_at": None, "last_sync_sha": None})
    records = make_records()
    store.put_evidence([record.model_dump(mode="json") for record in records])
    graph_store = InMemoryGraphStore() if use_graph else None
    if graph_store:
        graph_store.upsert(graph_from_evidence("repo_1", records))
    graph = GraphService(graph_store) if use_graph else None
    return RetrievalService(store, graph), records


def test_question_understanding_extracts_intent_and_entities() -> None:
    plan = understand_question("Why is `RETRY_MAX_ATTEMPTS` used in src/retry_policy.py?")
    assert plan.intent == "why"
    assert "RETRY_MAX_ATTEMPTS" in plan.entity_refs
    assert "src/retry_policy.py" in plan.entity_refs


def test_exact_and_keyword_search_ranks_relevant_evidence_higher(tmp_path) -> None:
    retriever, records = service(tmp_path, use_graph=False)
    result = retriever.retrieve("repo_1", "Why is retry_policy.py bounded?", result_limit=2)
    assert result.status == "found"
    assert result.hits[0].evidence_id in {records[0].evidence_id, records[1].evidence_id}
    assert result.hits[0].signals["entity_match"] > 0
    assert result.hits[-1].evidence_id != records[2].evidence_id


def test_graph_traversal_finds_related_issue_not_matching_file_text(tmp_path) -> None:
    retriever, records = service(tmp_path, use_graph=True)
    result = retriever.retrieve("repo_1", "Why is src/retry_policy.py bounded?", result_limit=10)
    issue_id = records[1].evidence_id
    assert issue_id in {hit.evidence_id for hit in result.hits}
    issue_hit = next(hit for hit in result.hits if hit.evidence_id == issue_id)
    assert issue_hit.graph_paths
    assert any("REFERENCES" in path.relationships for path in issue_hit.graph_paths)
    assert result.diagnostics["graph_matches"] >= 1


def test_duplicate_evidence_is_removed_and_limits_are_respected(tmp_path) -> None:
    retriever, records = service(tmp_path, use_graph=False)
    duplicate = records[0].model_copy(update={"title": "duplicate title"})
    retriever.store.put_evidence([duplicate.model_dump(mode="json")])
    result = retriever.retrieve("repo_1", "retry_policy.py", result_limit=1, context_limit=10)
    assert len(result.hits) == 1
    assert result.diagnostics["deduplicated_results"] == 2
    assert result.diagnostics["context_chars"] <= 10 or result.diagnostics["returned_results"] == 1


def test_empty_and_conflicting_results_are_explicit(tmp_path) -> None:
    retriever, _ = service(tmp_path, use_graph=False)
    empty = retriever.retrieve("repo_1", "quantum database migration", result_limit=5)
    assert empty.status == "insufficient"
    assert empty.hits == []

    conflict = normalize_github_source("repo_1", GitHubSource(source_id="github:a/b:issue:11", source_type="issue", title="Conflicting retry rationale", body="This contradicts the earlier explanation.", source_url="https://github.com/a/b/issues/11"))[0]
    retriever.store.put_evidence([conflict.model_dump(mode="json")])
    conflicting = retriever.retrieve("repo_1", "retry", result_limit=10)
    assert conflicting.status == "conflicting"
