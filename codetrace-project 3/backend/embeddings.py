from __future__ import annotations

import json
import logging
import math
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings
from .models import EvidenceRecord
from .store import Store

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    code = "embedding_error"


class EmbeddingUnavailable(EmbeddingError):
    code = "embedding_unavailable"


class EmbeddingTimeout(EmbeddingError):
    code = "embedding_timeout"


class EmbeddingModelUnavailable(EmbeddingError):
    code = "embedding_model_unavailable"


class EmbeddingMalformed(EmbeddingError):
    code = "embedding_malformed"


@dataclass(frozen=True)
class EmbeddingResult:
    vector: tuple[float, ...]
    model: str
    latency_ms: int
    reused: bool = False


RequestFn = Callable[[str, dict[str, Any], int], dict[str, Any]]


class EmbeddingService(Protocol):
    def embed(self, text: str) -> tuple[float, ...]: ...


class OllamaEmbeddingService:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 60, request: RequestFn | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._request_fn = request or self._request

    @classmethod
    def from_settings(cls, settings: Settings) -> "OllamaEmbeddingService":
        return cls(settings.ollama_base_url, settings.ollama_embedding_model, settings.ollama_timeout_seconds)

    def embed(self, text: str) -> tuple[float, ...]:
        started = time.monotonic()
        try:
            payload = self._request_fn(f"{self.base_url}/api/embed", {"model": self.model, "input": text}, self.timeout_seconds)
        except EmbeddingError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise EmbeddingTimeout("Ollama embedding request timed out") from exc
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            raise EmbeddingUnavailable("Ollama embeddings are unavailable") from exc
        values = payload.get("embeddings") if isinstance(payload, dict) else None
        if values is None and isinstance(payload, dict):
            values = [payload.get("embedding")]
        if not isinstance(values, list) or not values or not isinstance(values[0], list):
            raise EmbeddingMalformed("Ollama returned no embedding vector")
        try:
            vector = tuple(float(value) for value in values[0])
        except (TypeError, ValueError) as exc:
            raise EmbeddingMalformed("Ollama returned an invalid embedding vector") from exc
        if not vector or not all(math.isfinite(value) for value in vector):
            raise EmbeddingMalformed("Ollama returned an empty or non-finite embedding vector")
        logger.info("ollama_embedding_completed model=%s latency_ms=%d dimensions=%d", self.model, int((time.monotonic() - started) * 1000), len(vector))
        return vector

    def _request(self, url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404):
                raise EmbeddingModelUnavailable(f"Ollama embedding model '{self.model}' is unavailable") from exc
            if exc.code >= 500:
                raise EmbeddingUnavailable("Ollama returned a server error for embeddings") from exc
            raise EmbeddingError("Ollama rejected the embedding request") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            if isinstance(exc, TimeoutError) or "timed out" in str(exc).lower():
                raise EmbeddingTimeout("Ollama embedding request timed out") from exc
            raise EmbeddingUnavailable("Ollama embeddings are unavailable") from exc


class SemanticIndex:
    """A bounded SQLite-backed embedding cache; vectors are not a startup dependency."""

    def __init__(self, store: Store, service: EmbeddingService, model: str, max_candidates: int = 500, min_similarity: float = 0.15):
        self.store = store
        self.service = service
        self.model = model
        self.max_candidates = max(1, max_candidates)
        self.min_similarity = min_similarity
        self.last_reused = 0
        self.last_generated = 0

    def search(self, repository_id: str, question: str, records: list[EvidenceRecord], limit: int) -> list[tuple[str, float]]:
        self.last_reused = 0
        self.last_generated = 0
        query = self.service.embed(question)
        vectors: list[tuple[str, tuple[float, ...]]] = []
        for item in records[: self.max_candidates]:
            cached = self.store.get_embedding(item.evidence_id, item.content_hash, self.model)
            if cached is not None:
                vector = tuple(cached)
                self.last_reused += 1
            else:
                vector = self.service.embed(_embedding_text(item))
                self.store.put_embedding(item.evidence_id, repository_id, item.content_hash, self.model, vector)
                self.last_generated += 1
            vectors.append((item.evidence_id, vector))
        ranked = sorted(((evidence_id, _cosine(query, vector)) for evidence_id, vector in vectors), key=lambda pair: (-pair[1], pair[0]))
        return [(evidence_id, score) for evidence_id, score in ranked if score >= self.min_similarity][:limit]


def _embedding_text(item: EvidenceRecord) -> str:
    paths = " ".join(change.path for change in item.changed_files)
    return " ".join(filter(None, [item.title, item.summary, item.excerpt, paths]))[:6000]


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    size = min(len(left), len(right))
    if not size:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
