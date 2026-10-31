from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings
from .models import DecisionCandidate, EvidenceRecord, GraphEdge, GraphNode, GraphResponse, SupersessionAssessment


_PATH_RE = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_-]+)?")


class GraphUnavailable(RuntimeError):
    pass


class GraphStore(Protocol):
    available: bool

    def ensure_constraints(self) -> None: ...
    def upsert(self, graph: GraphResponse) -> None: ...
    def query(self, repository_id: str, node_types: list[str], depth: int, limit: int) -> GraphResponse: ...


@dataclass(frozen=True)
class GraphBounds:
    max_depth: int = 2
    max_nodes: int = 250
    timeout_seconds: int = 10


def stable_node_id(repository_id: str, node_type: str, source_id: str) -> str:
    return "node_" + hashlib.sha256(f"{repository_id}\x1f{node_type}\x1f{source_id}".encode()).hexdigest()[:32]


def stable_edge_id(repository_id: str, source: str, relationship_type: str, target: str, evidence_ids: Iterable[str] = ()) -> str:
    evidence = "\x1f".join(sorted(evidence_ids))
    return "edge_" + hashlib.sha256(f"{repository_id}\x1f{source}\x1f{relationship_type}\x1f{target}\x1f{evidence}".encode()).hexdigest()[:32]


def graph_from_evidence(repository_id: str, records: list[EvidenceRecord], confirmed_supersessions: list[tuple[str, str, list[str]]] | None = None, uncertain_supersessions: list[tuple[str, str, list[str]]] | None = None, decisions: list[DecisionCandidate] | None = None, supersession_assessments: list[SupersessionAssessment] | None = None) -> GraphResponse:
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}

    def add_node(node_type: str, source_id: str, label: str, metadata: dict[str, Any] | None = None, source_ids: list[str] | None = None) -> str:
        node_id = stable_node_id(repository_id, node_type, source_id)
        nodes.setdefault(node_id, GraphNode(id=node_id, repository_id=repository_id, node_type=node_type, label=label, metadata=metadata or {}, source_ids=source_ids or []))
        return node_id

    def add_edge(source: str, relationship_type: str, target: str, evidence_ids: list[str] | None = None, metadata: dict[str, Any] | None = None) -> None:
        evidence = evidence_ids or []
        edge_id = stable_edge_id(repository_id, source, relationship_type, target, evidence)
        edges.setdefault(edge_id, GraphEdge(id=edge_id, repository_id=repository_id, source=source, target=target, relationship_type=relationship_type, evidence_ids=evidence, metadata=metadata or {}))

    repo_node = add_node("repository", repository_id, repository_id)
    for record in records:
        evidence_node = add_node("evidence", record.evidence_id, record.title or record.source_id, {"source_type": record.source_type, "source_url": record.source_url, "observed_at": record.observed_at.isoformat() if record.observed_at else None}, [record.evidence_id])
        source_node = add_node(record.source_type, record.source_id, record.title or record.source_id, {"source_url": record.source_url, "observed_at": record.observed_at.isoformat() if record.observed_at else None}, [record.source_id])
        add_edge(repo_node, "CONTAINS", source_node)
        add_edge(source_node, "SUPPORTED_BY", evidence_node, [record.evidence_id])
        referenced_paths = {change.path: change for change in record.changed_files}
        for path in _PATH_RE.findall(" ".join(filter(None, [record.title, record.summary, record.excerpt]))):
            referenced_paths.setdefault(path, None)
        for path, file_change in referenced_paths.items():
            file_node = add_node("file", path, path, {"status": file_change.status, "line_ranges": [line.model_dump() for line in file_change.line_ranges]} if file_change else {})
            add_edge(file_node, "REFERENCES", evidence_node, [record.evidence_id])
            if record.source_type == "commit" and file_change:
                add_edge(file_node, "MODIFIED_BY", source_node, [record.evidence_id], {"status": file_change.status})
        if record.provenance.parent_source_ids:
            for parent_id in record.provenance.parent_source_ids:
                parent_node = add_node("issue", parent_id, parent_id)
                add_edge(source_node, "DISCUSSED_IN", parent_node, [record.evidence_id])

    known_evidence_ids = {record.evidence_id for record in records}
    for source_id, target_id, evidence_ids in confirmed_supersessions or []:
        source = add_node("decision", source_id, source_id)
        target = add_node("decision", target_id, target_id)
        if evidence_ids and set(evidence_ids).issubset(known_evidence_ids):
            add_edge(source, "SUPERSEDES", target, evidence_ids, {"certainty": "confirmed"})
        else:
            add_edge(source, "RELATED_TO", target, evidence_ids, {"candidate_relationship": "SUPERSEDES", "certainty": "uncertain", "reason": "missing_supporting_evidence"})
    for source_id, target_id, evidence_ids in uncertain_supersessions or []:
        source = add_node("decision", source_id, source_id)
        target = add_node("decision", target_id, target_id)
        add_edge(source, "RELATED_TO", target, evidence_ids, {"candidate_relationship": "SUPERSEDES", "certainty": "uncertain"})
    for decision in decisions or []:
        decision_node = add_node("decision", decision.decision_id, decision.statement, {"status": decision.status, "evidence_kind": decision.evidence_kind, "affected_paths": decision.affected_paths, "configuration_keys": decision.configuration_keys}, decision.evidence_ids)
        for evidence_id in decision.evidence_ids:
            evidence_node = add_node("evidence", evidence_id, evidence_id, source_ids=[evidence_id])
            add_edge(decision_node, "SUPPORTED_BY", evidence_node, [evidence_id])
        for path in decision.affected_paths:
            file_node = add_node("file", path, path)
            add_edge(decision_node, "AFFECTS", file_node, decision.evidence_ids)
    for assessment in supersession_assessments or []:
        source = add_node("decision", assessment.newer_decision_id, assessment.newer_decision_id)
        target = add_node("decision", assessment.older_decision_id, assessment.older_decision_id)
        relationship = "SUPERSEDES" if assessment.status == "confirmed" else "RELATED_TO"
        metadata = {"certainty": assessment.status, "candidate_relationship": "SUPERSEDES" if assessment.status != "confirmed" else None, "rationale": assessment.rationale}
        add_edge(source, relationship, target, assessment.evidence_ids, metadata)
    return GraphResponse(repository_id=repository_id, nodes=list(nodes.values()), edges=list(edges.values()))


class InMemoryGraphStore:
    available = True

    def __init__(self) -> None:
        self.graphs: dict[str, GraphResponse] = {}
        self.constraints_ready = False

    def ensure_constraints(self) -> None:
        self.constraints_ready = True

    def upsert(self, graph: GraphResponse) -> None:
        current = self.graphs.get(graph.repository_id)
        if not current:
            self.graphs[graph.repository_id] = graph
            return
        nodes = {node.id: node for node in current.nodes}
        nodes.update({node.id: node for node in graph.nodes})
        edges = {edge.id: edge for edge in current.edges}
        edges.update({edge.id: edge for edge in graph.edges})
        self.graphs[graph.repository_id] = GraphResponse(repository_id=graph.repository_id, nodes=list(nodes.values()), edges=list(edges.values()))

    def query(self, repository_id: str, node_types: list[str], depth: int, limit: int) -> GraphResponse:
        graph = self.graphs.get(repository_id, GraphResponse(repository_id=repository_id, nodes=[], edges=[]))
        nodes = [node for node in graph.nodes if not node_types or node.node_type in node_types][:limit]
        node_ids = {node.id for node in nodes}
        edges = [edge for edge in graph.edges if edge.source in node_ids and edge.target in node_ids][:limit]
        return GraphResponse(repository_id=repository_id, nodes=nodes, edges=edges, truncated=len(graph.nodes) > len(nodes) or len(graph.edges) > len(edges))


class Neo4jGraphStore:
    available = True
    _DEPTH_QUERIES = {
        0: "MATCH (n:Entity {repository_id: $repository_id}) WHERE ($node_types = [] OR n.node_type IN $node_types) RETURN n LIMIT $limit",
        1: "MATCH (start:Entity {repository_id: $repository_id})-[rels:RELATES*0..1]-(n:Entity {repository_id: $repository_id}) WHERE ($node_types = [] OR n.node_type IN $node_types) RETURN start, rels, n LIMIT $limit",
        2: "MATCH (start:Entity {repository_id: $repository_id})-[rels:RELATES*0..2]-(n:Entity {repository_id: $repository_id}) WHERE ($node_types = [] OR n.node_type IN $node_types) RETURN start, rels, n LIMIT $limit",
        3: "MATCH (start:Entity {repository_id: $repository_id})-[rels:RELATES*0..3]-(n:Entity {repository_id: $repository_id}) WHERE ($node_types = [] OR n.node_type IN $node_types) RETURN start, rels, n LIMIT $limit",
    }

    def __init__(self, driver: Any, database: str, bounds: GraphBounds):
        self.driver = driver
        self.database = database
        self.bounds = bounds

    @classmethod
    def from_settings(cls, settings: Settings, bounds: GraphBounds | None = None) -> "Neo4jGraphStore | None":
        if not settings.neo4j_uri or not settings.neo4j_username or not settings.neo4j_password:
            return None
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password), connection_timeout=settings.ingestion_timeout_seconds)
            return cls(driver, settings.neo4j_database, bounds or GraphBounds(timeout_seconds=settings.ingestion_timeout_seconds))
        except Exception:
            return None

    def ensure_constraints(self) -> None:
        statements = [
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE",
            "CREATE INDEX entity_repository_id IF NOT EXISTS FOR (n:Entity) ON (n.repository_id)",
        ]
        try:
            with self.driver.session(database=self.database) as session:
                for statement in statements:
                    session.run(statement).consume()
        except Exception as exc:
            raise GraphUnavailable("Neo4j constraints are unavailable") from exc

    def upsert(self, graph: GraphResponse) -> None:
        try:
            with self.driver.session(database=self.database) as session:
                for node in graph.nodes:
                    session.run("MERGE (n:Entity {id: $id}) SET n.repository_id=$repository_id, n.node_type=$node_type, n.label=$label, n.metadata=$metadata, n.source_ids=$source_ids", **node.model_dump()).consume()
                for edge in graph.edges:
                    session.run("MATCH (s:Entity {id: $source, repository_id: $repository_id}), (t:Entity {id: $target, repository_id: $repository_id}) MERGE (s)-[r:RELATES {id: $id}]->(t) SET r.relationship_type=$relationship_type, r.evidence_ids=$evidence_ids, r.metadata=$metadata", **edge.model_dump()).consume()
        except Exception as exc:
            raise GraphUnavailable("Neo4j graph write failed") from exc

    def query(self, repository_id: str, node_types: list[str], depth: int, limit: int) -> GraphResponse:
        depth = min(max(depth, 0), self.bounds.max_depth)
        limit = min(max(limit, 1), self.bounds.max_nodes)
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(self._DEPTH_QUERIES[depth], repository_id=repository_id, node_types=node_types, limit=limit, timeout=self.bounds.timeout_seconds)
                return self._result_to_graph(repository_id, result, limit)
        except Exception as exc:
            raise GraphUnavailable("Neo4j graph query failed") from exc

    @staticmethod
    def _result_to_graph(repository_id: str, result: Any, limit: int) -> GraphResponse:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        for row in result:
            values = row.values()
            for value in values:
                if hasattr(value, "items") and "id" in value:
                    node = GraphNode(id=value["id"], repository_id=value["repository_id"], node_type=value["node_type"], label=value["label"], metadata=value.get("metadata") or {}, source_ids=value.get("source_ids") or [])
                    nodes[node.id] = node
                if isinstance(value, list):
                    for relationship in value:
                        if hasattr(relationship, "items"):
                            edge = GraphEdge(id=relationship["id"], repository_id=repository_id, source=relationship.start_node["id"], target=relationship.end_node["id"], relationship_type=relationship["relationship_type"], evidence_ids=relationship.get("evidence_ids") or [], metadata=relationship.get("metadata") or {})
                            edges[edge.id] = edge
        return GraphResponse(repository_id=repository_id, nodes=list(nodes.values())[:limit], edges=list(edges.values())[:limit], truncated=len(nodes) > limit or len(edges) > limit)


class GraphService:
    def __init__(self, store: GraphStore | None, bounds: GraphBounds | None = None):
        self.store = store
        self.bounds = bounds or GraphBounds()

    @classmethod
    def from_settings(cls, settings: Settings) -> "GraphService":
        return cls(Neo4jGraphStore.from_settings(settings), GraphBounds(timeout_seconds=settings.ingestion_timeout_seconds))

    def upsert_evidence(self, repository_id: str, records: list[EvidenceRecord], decisions: list[DecisionCandidate] | None = None, supersessions: list[SupersessionAssessment] | None = None) -> list[str]:
        if not self.store:
            return ["neo4j_unavailable"]
        graph = graph_from_evidence(repository_id, records, decisions=decisions, supersession_assessments=supersessions)
        try:
            self.store.ensure_constraints()
            self.store.upsert(graph)
            return []
        except GraphUnavailable:
            return ["neo4j_unavailable"]

    def get(self, repository_id: str, node_types: list[str] | None = None, depth: int = 1, limit: int = 100) -> GraphResponse:
        node_types = node_types or []
        safe_types = [node_type for node_type in node_types if node_type in {"repository", "file", "code_entity", "configuration_key", "commit", "pull_request", "issue", "discussion", "comment", "documentation", "incident", "decision_record", "code_change", "code_excerpt", "evidence", "decision", "person"}]
        depth = min(max(depth, 0), self.bounds.max_depth)
        limit = min(max(limit, 1), self.bounds.max_nodes)
        if not self.store:
            return GraphResponse(repository_id=repository_id, nodes=[], edges=[], available=False, warnings=["neo4j_unavailable"])
        try:
            return self.store.query(repository_id, safe_types, depth, limit)
        except GraphUnavailable:
            return GraphResponse(repository_id=repository_id, nodes=[], edges=[], available=False, warnings=["neo4j_unavailable"])
