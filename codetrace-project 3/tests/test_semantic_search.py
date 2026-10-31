from __future__ import annotations

from datetime import datetime, timezone

from backend.embeddings import EmbeddingError, OllamaEmbeddingService
from backend.evidence import normalize_github_source
from backend.models import GitHubSource
from backend.retrieval import RetrievalService
from backend.store import Store


class FakeEmbeddings:
    def __init__(self, vectors: dict[str, tuple[float, ...]] | None = None, fail: bool = False):
        self.vectors = vectors or {}
        self.calls: list[str] = []
        self.fail = fail

    def embed(self, text: str) -> tuple[float, ...]:
        self.calls.append(text)
        if self.fail:
            raise EmbeddingError("embedding unavailable")
        for key, vector in self.vectors.items():
            if key in text:
                return vector
        return (0.0, 1.0)


def records():
    return [
        normalize_github_source("repo_1", GitHubSource(source_id="issue:1", source_type="issue", title="Rate limit protection", body="Use a gateway budget to protect upstream traffic.", source_url="https://github.com/a/b/issues/1", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))[0],
        normalize_github_source("repo_1", GitHubSource(source_id="issue:2", source_type="issue", title="Button color", body="Update the UI color.", source_url="https://github.com/a/b/issues/2"))[0],
    ]


def semantic_service(tmp_path, fake: FakeEmbeddings):
    store = Store(tmp_path / "state.sqlite3")
    store.upsert_repository({"id": "repo_1", "full_name": "a/b", "remote_url": "https://github.com/a/b.git", "default_branch": "main", "index_status": "indexed", "last_indexed_at": None, "last_sync_sha": None})
    values = records()
    store.put_evidence([item.model_dump(mode="json") for item in values])
    settings = type("Settings", (), {"retrieval_result_limit": 20, "retrieval_context_limit": 12000, "ollama_embedding_model": "fake", "semantic_max_candidates": 500, "semantic_min_similarity": 15})()
    return RetrievalService(store, settings=settings, embedding_service=fake), store, values


def test_similar_wording_is_retrieved_and_duplicate_is_merged(tmp_path):
    fake = FakeEmbeddings({"protect upstream": (1.0, 0.0), "Rate limit": (1.0, 0.0), "Button": (0.0, 1.0)})
    retriever, _, values = semantic_service(tmp_path, fake)
    result = retriever.retrieve("repo_1", "protect upstream traffic", result_limit=10)
    assert result.hits[0].evidence_id == values[0].evidence_id
    assert result.hits[0].signals["semantic_similarity"] > 0.9
    assert len({hit.evidence_id for hit in result.hits}) == len(result.hits)


def test_unrelated_semantic_result_ranks_lower(tmp_path):
    fake = FakeEmbeddings({"protect upstream": (1.0, 0.0), "Button": (0.0, 1.0)})
    retriever, _, values = semantic_service(tmp_path, fake)
    result = retriever.retrieve("repo_1", "protect upstream", result_limit=10)
    positions = {hit.evidence_id: hit.rank for hit in result.hits}
    assert positions[values[0].evidence_id] == 1
    assert values[1].evidence_id not in positions


def test_embedding_reused_then_invalidated_when_source_hash_changes(tmp_path):
    fake = FakeEmbeddings({"Rate limit": (1.0, 0.0), "protect": (1.0, 0.0)})
    retriever, store, values = semantic_service(tmp_path, fake)
    retriever.retrieve("repo_1", "protect", result_limit=10)
    first_call_count = len(fake.calls)
    retriever.retrieve("repo_1", "protect", result_limit=10)
    assert len(fake.calls) == first_call_count + 1  # query embedding; evidence vectors are reused
    changed = values[0].model_copy(update={"summary": "Changed source wording", "content_hash": "changed-hash"})
    store.put_evidence([changed.model_dump(mode="json")])
    retriever.retrieve("repo_1", "protect", result_limit=10)
    assert len(fake.calls) == first_call_count + 3  # query plus one regenerated source vector


def test_embedding_failure_falls_back_to_keyword_retrieval(tmp_path):
    fake = FakeEmbeddings(fail=True)
    retriever, _, values = semantic_service(tmp_path, fake)
    result = retriever.retrieve("repo_1", "Rate limit", result_limit=10)
    assert values[0].evidence_id in {hit.evidence_id for hit in result.hits}
    assert "embedding_error" in result.warnings


def test_ollama_embedding_adapter_accepts_structured_response():
    calls = []

    def request(url, payload, timeout):
        calls.append((url, payload, timeout))
        return {"embeddings": [[0.25, 0.75]]}

    service = OllamaEmbeddingService("http://ollama.test", "embed-model", request=request)
    assert service.embed("text") == (0.25, 0.75)
    assert calls[0][0].endswith("/api/embed")
