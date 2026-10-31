from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable

from .config import Settings
from .embeddings import EmbeddingError, SemanticIndex
from .graph import GraphService
from .models import EvidenceRecord, GraphPath, GraphPathNode, GraphResponse, RetrievalHit, RetrievalResult
from .store import Store


_STOPWORDS = {"a", "an", "and", "are", "does", "for", "how", "is", "it", "of", "on", "the", "this", "to", "was", "what", "why", "in", "with"}
_PATH = re.compile(r"(?<![\w/.-])(?:[\w.-]+/)+[\w.-]+(?:\.[A-Za-z0-9_-]+)?")
_FILE = re.compile(r"\b[A-Za-z0-9_.-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|yaml|yml|json|toml|md)\b")
_CONFIG = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
_FUNCTION = re.compile(r"\b[A-Za-z_][A-Za-z0-9_.]*\s*\(")


@dataclass(frozen=True)
class QuestionPlan:
    normalized: str
    intent: str
    terms: tuple[str, ...]
    entity_refs: tuple[str, ...]


class RetrievalService:
    """Evidence retrieval independent from answer generation."""

    def __init__(self, store: Store, graph: GraphService | None = None, settings: Settings | None = None, embedding_service=None):
        self.store = store
        self.graph = graph
        self.result_limit = settings.retrieval_result_limit if settings else 20
        self.context_limit = settings.retrieval_context_limit if settings else 12_000
        self.graph_depth = 2
        self.graph_limit = max(self.result_limit * 8, 50)
        self.semantic: SemanticIndex | None = None
        if embedding_service is not None:
            self.semantic = SemanticIndex(store, embedding_service, settings.ollama_embedding_model if settings else "nomic-embed-text", settings.semantic_max_candidates if settings else 500, (settings.semantic_min_similarity if settings else 15) / 100)

    def retrieve(self, repository_id: str, question: str, result_limit: int | None = None, context_limit: int | None = None) -> RetrievalResult:
        plan = understand_question(question)
        limit = min(max(result_limit or self.result_limit, 1), 100)
        context_limit = min(max(context_limit or self.context_limit, 500), 100_000)
        raw_items = [EvidenceRecord.model_validate(item) for item in self.store.list_evidence(repository_id)]
        by_id = {item.evidence_id: item for item in raw_items}
        by_source_id = {item.source_id: item.evidence_id for item in raw_items}
        direct: dict[str, tuple[float, dict[str, float], list[str]]] = {}
        for item in raw_items:
            score, signals, matched = self._score(item, plan)
            if score > 0:
                direct[item.evidence_id] = (score, signals, matched)

        warnings: list[str] = []
        semantic_matches: list[tuple[str, float]] = []
        semantic_reused = semantic_generated = 0
        if self.semantic:
            try:
                semantic_matches = self.semantic.search(repository_id, plan.normalized, raw_items, limit)
                semantic_reused = self.semantic.last_reused
                semantic_generated = self.semantic.last_generated
            except EmbeddingError as exc:
                warnings.append(exc.code)
        graph_paths_by_evidence: dict[str, list[GraphPath]] = defaultdict(list)
        graph_matches: set[str] = set()
        if self.graph:
            graph = self.graph.get(repository_id, depth=self.graph_depth, limit=self.graph_limit)
            warnings.extend(graph.warnings)
            if graph.available:
                graph_paths_by_evidence, graph_matches = self._graph_context(graph, plan, by_id, by_source_id)

        merged: dict[str, tuple[float, dict[str, float], list[str]]] = dict(direct)
        for evidence_id in graph_matches:
            score, signals, matched = merged.get(evidence_id, (0.0, {}, []))
            signals = dict(signals)
            signals["graph_relationship"] = 1.0
            matched = list(matched)
            merged[evidence_id] = (score + 0.35, signals, matched)
        for evidence_id, similarity in semantic_matches:
            score, signals, matched = merged.get(evidence_id, (0.0, {}, []))
            signals = dict(signals)
            signals["semantic_similarity"] = round(similarity, 4)
            merged[evidence_id] = (score + 0.35 * similarity, signals, list(matched))

        ranked = sorted(merged.items(), key=lambda pair: (-pair[1][0], pair[0]))
        hits: list[RetrievalHit] = []
        used_chars = 0
        for evidence_id, (score, signals, matched) in ranked:
            item = by_id[evidence_id]
            excerpt = item.excerpt
            item_chars = len(excerpt or "")
            if hits and used_chars + item_chars > context_limit:
                continue
            used_chars += item_chars
            hits.append(RetrievalHit(evidence_id=evidence_id, score=round(score, 4), rank=len(hits) + 1, signals=signals, matched_terms=sorted(set(matched)), title=item.title, source_type=item.source_type, observed_at=item.observed_at, source_url=item.source_url, excerpt=excerpt, graph_paths=graph_paths_by_evidence.get(evidence_id, [])))
            if len(hits) >= limit:
                break

        status = "found" if hits else "insufficient"
        if hits and _has_conflict([by_id[hit.evidence_id] for hit in hits]):
            status = "conflicting"
        all_paths = [path for paths in graph_paths_by_evidence.values() for path in paths]
        return RetrievalResult(repository_id=repository_id, question=question, normalized_question=plan.normalized, intent=plan.intent, status=status, hits=hits, graph_paths=_dedup_paths(all_paths), warnings=sorted(set(warnings)), diagnostics={"indexed_evidence": len(raw_items), "direct_matches": len(direct), "graph_matches": len(graph_matches), "semantic_matches": len(semantic_matches), "semantic_reused": semantic_reused, "semantic_generated": semantic_generated, "deduplicated_results": len(merged), "returned_results": len(hits), "context_chars": used_chars, "result_limit": limit, "context_limit": context_limit})

    @staticmethod
    def _score(item: EvidenceRecord, plan: QuestionPlan) -> tuple[float, dict[str, float], list[str]]:
        text = " ".join(filter(None, [item.title, item.summary, item.excerpt, item.source_id, *[change.path for change in item.changed_files]])).lower()
        matched = [term for term in plan.terms if term in text]
        entity_matches = [entity for entity in plan.entity_refs if entity.lower() in text]
        exact = 1.0 if any(entity.lower() in text for entity in plan.entity_refs) else 0.0
        keyword = min(len(set(matched)) / max(len(set(plan.terms)), 1), 1.0)
        source_relevance = {"issue": 1.0, "pull_request": 1.0, "discussion": 1.0, "documentation": 0.9, "comment": 0.85, "decision_record": 0.95, "commit": 0.8, "code_change": 0.75}.get(item.source_type, 0.5)
        temporal = 1.0 if item.observed_at else 0.0
        signals = {"entity_match": min(len(entity_matches) / max(len(plan.entity_refs), 1), 1.0), "exact_match": exact, "keyword_match": keyword, "source_relevance": source_relevance, "temporal_relevance": temporal}
        score = signals["entity_match"] * 0.4 + signals["exact_match"] * 0.25 + signals["keyword_match"] * 0.2 + signals["source_relevance"] * 0.1 + signals["temporal_relevance"] * 0.05
        if not matched and not entity_matches:
            score = 0.0
        return score, signals, matched + entity_matches

    @staticmethod
    def _graph_context(graph: GraphResponse, plan: QuestionPlan, by_id: dict[str, EvidenceRecord], by_source_id: dict[str, str]) -> tuple[dict[str, list[GraphPath]], set[str]]:
        node_by_id = {node.id: node for node in graph.nodes}
        adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge in graph.edges:
            adjacency[edge.source].append((edge.target, edge.relationship_type))
            adjacency[edge.target].append((edge.source, edge.relationship_type))
        seeds = [node.id for node in graph.nodes if any(term.lower() in node.label.lower() for term in plan.entity_refs + plan.terms)]
        paths: dict[str, list[GraphPath]] = defaultdict(list)
        matches: set[str] = set()
        for seed in seeds:
            queue = deque([(seed, [seed], [])])
            visited = {(seed, 0)}
            while queue:
                node_id, node_path, rel_path = queue.popleft()
                node = node_by_id[node_id]
                evidence_ids = set(node.source_ids)
                if node.node_type == "evidence":
                    evidence_ids.add(node.source_ids[0] if node.source_ids else node_id)
                for source_id in list(evidence_ids):
                    evidence_id = source_id if source_id in by_id else by_source_id.get(source_id)
                    if evidence_id:
                        matches.add(evidence_id)
                        paths[evidence_id].append(GraphPath(nodes=[GraphPathNode(id=node_by_id[path_node].id, label=node_by_id[path_node].label, node_type=node_by_id[path_node].node_type) for path_node in node_path], relationships=rel_path))
                if len(node_path) - 1 >= 2:
                    continue
                for next_id, relationship in adjacency[node_id]:
                    state = (next_id, len(node_path))
                    if next_id not in node_path and state not in visited:
                        visited.add(state)
                        queue.append((next_id, node_path + [next_id], rel_path + [relationship]))
        return {evidence_id: _dedup_paths(item_paths)[:3] for evidence_id, item_paths in paths.items()}, matches


def understand_question(question: str) -> QuestionPlan:
    normalized = " ".join(question.strip().split())
    lower = normalized.lower()
    if lower.startswith("why") or " why " in f" {lower} ":
        intent = "why"
    elif any(phrase in lower for phrase in ("what changed", "between", "changed from", "difference")):
        intent = "what_changed"
    elif any(phrase in lower for phrase in ("current", "still", "now", "today")):
        intent = "current"
    elif any(phrase in lower for phrase in ("evidence", "support", "prove")):
        intent = "support"
    else:
        intent = "unknown"
    refs = set(re.findall(r"`([^`]+)`", normalized))
    refs.update(_PATH.findall(normalized))
    refs.update(_FILE.findall(normalized))
    refs.update(token.rstrip("(") for token in _FUNCTION.findall(normalized))
    refs.update(_CONFIG.findall(normalized))
    terms = tuple(sorted({token.lower() for token in re.findall(r"[A-Za-z0-9_./-]{2,}", normalized) if token.lower() not in _STOPWORDS}))
    return QuestionPlan(normalized=normalized, intent=intent, terms=terms, entity_refs=tuple(sorted(refs)))


def _has_conflict(records: Iterable[EvidenceRecord]) -> bool:
    markers = ("conflict", "contradict", "disagree", "unclear", "not supported", "superseded")
    return any(any(marker in " ".join(filter(None, [record.title, record.summary, record.excerpt])).lower() for marker in markers) for record in records)


def _dedup_paths(paths: list[GraphPath]) -> list[GraphPath]:
    unique: dict[tuple[str, ...], GraphPath] = {}
    for path in paths:
        key = tuple(node.id for node in path.nodes) + tuple(path.relationships)
        unique[key] = path
    return list(unique.values())
