from __future__ import annotations

from datetime import datetime, timezone

from backend.evidence import normalize_commit, normalize_github_source
from backend.graph import GraphBounds, GraphService, InMemoryGraphStore, Neo4jGraphStore, graph_from_evidence, stable_edge_id, stable_node_id
from backend.models import GitCommit, GitHubSource


def records(repository_id: str = "repo_1"):
    commit, _ = normalize_commit(repository_id, GitCommit(
        source_id="git:abc", sha="abc", message="fix retry", author_name="A", authored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        changed_paths=["src/retry.py"], source_url="https://github.com/a/b/commit/abc",
    ))
    issue, _ = normalize_github_source(repository_id, GitHubSource(
        source_id="github:a/b:issue:1", source_type="issue", title="Retry context", body="context", source_url="https://github.com/a/b/issues/1",
    ))
    return [commit, issue]


def test_graph_ids_are_stable_and_memory_upsert_is_idempotent() -> None:
    graph = graph_from_evidence("repo_1", records())
    assert stable_node_id("repo_1", "file", "src/retry.py") == stable_node_id("repo_1", "file", "src/retry.py")
    assert stable_edge_id("repo_1", "a", "REFERENCES", "b", ["e2", "e1"]) == stable_edge_id("repo_1", "a", "REFERENCES", "b", ["e1", "e2"])
    store = InMemoryGraphStore()
    store.upsert(graph)
    store.upsert(graph)
    result = store.query("repo_1", [], 1, 250)
    assert len(result.nodes) == len(graph.nodes)
    assert len(result.edges) == len(graph.edges)
    assert store.constraints_ready is False


def test_graph_is_repository_scoped_and_bounded() -> None:
    store = InMemoryGraphStore()
    store.upsert(graph_from_evidence("repo_1", records("repo_1")))
    store.upsert(graph_from_evidence("repo_2", records("repo_2")))
    result = store.query("repo_1", ["file"], 99, 1)
    assert result.nodes
    assert all(node.repository_id == "repo_1" and node.node_type == "file" for node in result.nodes)
    assert all(edge.repository_id == "repo_1" for edge in result.edges)
    assert result.truncated


def test_supersession_requires_explicit_evidence_and_uncertain_links_are_not_supersedes() -> None:
    evidence_id = records()[0].evidence_id
    no_links = graph_from_evidence("repo_1", records())
    assert not [edge for edge in no_links.edges if edge.relationship_type == "SUPERSEDES"]
    uncertain = graph_from_evidence("repo_1", records(), uncertain_supersessions=[("new", "old", [evidence_id])])
    candidate = [edge for edge in uncertain.edges if edge.metadata.get("candidate_relationship") == "SUPERSEDES"]
    assert candidate and candidate[0].relationship_type == "RELATED_TO"
    confirmed = graph_from_evidence("repo_1", records(), confirmed_supersessions=[("new", "old", [evidence_id])])
    supersedes = [edge for edge in confirmed.edges if edge.relationship_type == "SUPERSEDES"]
    assert supersedes and supersedes[0].evidence_ids == [evidence_id]
    unsupported = graph_from_evidence("repo_1", records(), confirmed_supersessions=[("new", "old", ["missing"])])
    assert not [edge for edge in unsupported.edges if edge.relationship_type == "SUPERSEDES"]


def test_graph_service_returns_explicit_empty_response_without_neo4j() -> None:
    response = GraphService(None).get("repo_missing", depth=99, limit=1000)
    assert response.available is False
    assert response.nodes == []
    assert response.edges == []
    assert response.warnings == ["neo4j_unavailable"]


class FakeResult:
    def consume(self):
        return None

    def __iter__(self):
        return iter(())


class FakeSession:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, query, **params):
        self.calls.append((query, params))
        return FakeResult()


class FakeDriver:
    def __init__(self):
        self.session_instance = FakeSession()

    def session(self, **_kwargs):
        return self.session_instance


def test_neo4j_adapter_uses_constraints_and_parameterized_bounded_queries() -> None:
    driver = FakeDriver()
    adapter = Neo4jGraphStore(driver, "neo4j", GraphBounds(max_depth=3, max_nodes=250, timeout_seconds=2))
    adapter.ensure_constraints()
    adapter.upsert(graph_from_evidence("repo_1", records()))
    result = adapter.query("repo_1", ["file"], depth=99, limit=1000)
    assert result.nodes == []
    query, params = driver.session_instance.calls[-1]
    assert "repository_id: $repository_id" in query
    assert params["repository_id"] == "repo_1"
    assert params["limit"] == 250
    assert params["node_types"] == ["file"]
