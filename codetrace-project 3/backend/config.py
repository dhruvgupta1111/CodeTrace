from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    if value.lower() in {"1", "true", "yes", "on"}:
        return True
    if value.lower() in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    repository_cache_dir: Path
    github_token: str | None
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None
    neo4j_database: str = "neo4j"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 60
    ollama_context_limit: int = 12_000
    ollama_max_output_tokens: int = 800
    semantic_search_enabled: bool = False
    ollama_embedding_model: str = "nomic-embed-text"
    semantic_max_candidates: int = 500
    semantic_min_similarity: int = 15
    retrieval_result_limit: int = 20
    retrieval_context_limit: int = 12_000
    max_commits: int = 5000
    max_diff_bytes: int = 50_000_000
    max_file_bytes: int = 1_000_000
    max_documents: int = 100
    ingestion_timeout_seconds: int = 120
    github_page_size: int = 100
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("CODETRACE_DATA_DIR", ".codetrace")).resolve()
        cache_dir = Path(os.getenv("CODETRACE_REPOSITORY_CACHE_DIR", str(data_dir / "repositories"))).resolve()
        ollama_base_url = os.getenv("CODETRACE_OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        parsed_ollama_url = urlparse(ollama_base_url)
        if parsed_ollama_url.scheme not in {"http", "https"} or not parsed_ollama_url.netloc or parsed_ollama_url.username or parsed_ollama_url.password:
            raise ValueError("CODETRACE_OLLAMA_BASE_URL must be an http(s) URL without credentials")
        return cls(
            data_dir=data_dir,
            repository_cache_dir=cache_dir,
            github_token=os.getenv("GITHUB_TOKEN") or None,
            neo4j_uri=os.getenv("CODETRACE_NEO4J_URI") or None,
            neo4j_username=os.getenv("CODETRACE_NEO4J_USERNAME") or None,
            neo4j_password=os.getenv("CODETRACE_NEO4J_PASSWORD") or None,
            neo4j_database=os.getenv("CODETRACE_NEO4J_DATABASE", "neo4j"),
            ollama_base_url=ollama_base_url,
            ollama_model=os.getenv("CODETRACE_OLLAMA_MODEL", "llama3.1:8b"),
            ollama_timeout_seconds=_int_env("CODETRACE_OLLAMA_TIMEOUT_SECONDS", 60),
            ollama_context_limit=_int_env("CODETRACE_OLLAMA_CONTEXT_LIMIT", 12_000),
            ollama_max_output_tokens=_int_env("CODETRACE_OLLAMA_MAX_OUTPUT_TOKENS", 800),
            semantic_search_enabled=_bool_env("CODETRACE_SEMANTIC_SEARCH_ENABLED", False),
            ollama_embedding_model=os.getenv("CODETRACE_OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            semantic_max_candidates=_int_env("CODETRACE_SEMANTIC_MAX_CANDIDATES", 500),
            semantic_min_similarity=_int_env("CODETRACE_SEMANTIC_MIN_SIMILARITY_PERCENT", 15),
            retrieval_result_limit=_int_env("CODETRACE_RETRIEVAL_RESULT_LIMIT", 20),
            retrieval_context_limit=_int_env("CODETRACE_RETRIEVAL_CONTEXT_LIMIT", 12_000),
            max_commits=_int_env("CODETRACE_MAX_COMMITS", 5000),
            max_diff_bytes=_int_env("CODETRACE_MAX_DIFF_BYTES", 50_000_000),
            max_file_bytes=_int_env("CODETRACE_MAX_FILE_BYTES", 1_000_000),
            max_documents=_int_env("CODETRACE_MAX_DOCUMENTS", 100),
            ingestion_timeout_seconds=_int_env("CODETRACE_INGESTION_TIMEOUT_SECONDS", 120),
            cors_origins=tuple(origin.strip() for origin in os.getenv("CODETRACE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.repository_cache_dir.mkdir(parents=True, exist_ok=True)
