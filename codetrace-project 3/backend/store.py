from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS repositories (
              id TEXT PRIMARY KEY, full_name TEXT NOT NULL UNIQUE, remote_url TEXT NOT NULL,
              default_branch TEXT, index_status TEXT NOT NULL, last_indexed_at TEXT,
              last_sync_sha TEXT, counts_json TEXT
            );
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, status TEXT NOT NULL,
              progress REAL, stage TEXT, error_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sources (
              source_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, source_type TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS raw_sources (
              raw_source_ref TEXT PRIMARY KEY, repository_id TEXT NOT NULL, source_id TEXT NOT NULL,
              source_type TEXT NOT NULL, content_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence (
              evidence_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, source_id TEXT NOT NULL,
              source_type TEXT NOT NULL, content_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decisions (
              decision_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS supersession_assessments (
              assessment_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS embeddings (
              evidence_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, content_hash TEXT NOT NULL,
              model TEXT NOT NULL, dimensions INTEGER NOT NULL, vector_json TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def upsert_repository(self, repository: dict[str, Any]) -> dict[str, Any]:
        self.connection.execute(
            """INSERT INTO repositories(id, full_name, remote_url, default_branch, index_status, last_indexed_at, last_sync_sha, counts_json)
               VALUES (:id, :full_name, :remote_url, :default_branch, :index_status, :last_indexed_at, :last_sync_sha, :counts_json)
               ON CONFLICT(id) DO UPDATE SET remote_url=excluded.remote_url, default_branch=COALESCE(excluded.default_branch, repositories.default_branch)""",
            {**repository, "counts_json": json.dumps(repository.get("counts")) if repository.get("counts") is not None else None},
        )
        self.connection.commit()
        return self.get_repository(repository["id"])

    def get_repository(self, repository_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM repositories WHERE id = ?", (repository_id,)).fetchone()
        return self._repository(row) if row else None

    def list_repositories(self) -> list[dict[str, Any]]:
        return [self._repository(row) for row in self.connection.execute("SELECT * FROM repositories ORDER BY full_name")]

    def update_repository(self, repository_id: str, **values: Any) -> None:
        allowed = {"default_branch", "index_status", "last_indexed_at", "last_sync_sha", "counts_json"}
        values = {key: value for key, value in values.items() if key in allowed}
        if "counts_json" in values and not isinstance(values["counts_json"], (str, bytes, type(None))):
            values["counts_json"] = json.dumps(values["counts_json"])
        if not values:
            return
        assignments = ", ".join(f"{key} = ?" for key in values)
        self.connection.execute(f"UPDATE repositories SET {assignments} WHERE id = ?", (*values.values(), repository_id))
        self.connection.commit()

    def create_job(self, job_id: str, repository_id: str) -> dict[str, Any]:
        timestamp = now()
        self.connection.execute(
            "INSERT INTO jobs(id, repository_id, status, progress, stage, created_at, updated_at) VALUES (?, ?, 'pending', NULL, 'queued', ?, ?)",
            (job_id, repository_id, timestamp, timestamp),
        )
        self.connection.commit()
        return self.get_job(job_id)

    def get_active_job(self, repository_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM jobs WHERE repository_id = ? AND status IN ('pending', 'running') ORDER BY created_at DESC LIMIT 1", (repository_id,)).fetchone()
        if not row:
            return None
        value = dict(row)
        value["error"] = json.loads(value.pop("error_json")) if value.get("error_json") else None
        return value

    def update_job(self, job_id: str, **values: Any) -> None:
        values["updated_at"] = now()
        if "error" in values:
            values["error_json"] = json.dumps(values.pop("error")) if values["error"] is not None else None
        assignments = ", ".join(f"{key} = ?" for key in values)
        self.connection.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", (*values.values(), job_id))
        self.connection.commit()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        value = dict(row)
        value["error"] = json.loads(value.pop("error_json")) if value.get("error_json") else None
        return value

    def put_sources(self, repository_id: str, sources: list[dict[str, Any]]) -> None:
        self.connection.executemany(
            "INSERT INTO sources(source_id, repository_id, source_type, payload_json) VALUES (?, ?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET payload_json=excluded.payload_json",
            [(source["source_id"], repository_id, source["source_type"], json.dumps(source)) for source in sources],
        )
        self.connection.commit()

    def put_raw_source(self, repository_id: str, source: dict[str, Any], raw_source_ref: str, content_hash: str) -> None:
        self.connection.execute(
            """INSERT INTO raw_sources(raw_source_ref, repository_id, source_id, source_type, content_hash, payload_json, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(raw_source_ref) DO UPDATE SET content_hash=excluded.content_hash, payload_json=excluded.payload_json, updated_at=excluded.updated_at""",
            (raw_source_ref, repository_id, source["source_id"], source["source_type"], content_hash, json.dumps(source, ensure_ascii=False), now()),
        )
        self.connection.commit()

    def put_evidence(self, records: list[dict[str, Any]]) -> None:
        self.connection.executemany(
            """INSERT INTO evidence(evidence_id, repository_id, source_id, source_type, content_hash, payload_json, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(evidence_id) DO UPDATE SET content_hash=excluded.content_hash, payload_json=excluded.payload_json, updated_at=excluded.updated_at""",
            [(record["evidence_id"], record["repository_id"], record["source_id"], record["source_type"], record["content_hash"], json.dumps(record, ensure_ascii=False), now()) for record in records],
        )
        self.connection.commit()

    def list_evidence(self, repository_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT payload_json FROM evidence WHERE repository_id = ? ORDER BY updated_at", (repository_id,))
        return [json.loads(row["payload_json"]) for row in rows]

    def get_embedding(self, evidence_id: str, content_hash: str, model: str) -> list[float] | None:
        row = self.connection.execute("SELECT vector_json FROM embeddings WHERE evidence_id = ? AND content_hash = ? AND model = ?", (evidence_id, content_hash, model)).fetchone()
        return json.loads(row["vector_json"]) if row else None

    def put_embedding(self, evidence_id: str, repository_id: str, content_hash: str, model: str, vector: tuple[float, ...]) -> None:
        self.connection.execute(
            """INSERT INTO embeddings(evidence_id, repository_id, content_hash, model, dimensions, vector_json, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(evidence_id) DO UPDATE SET repository_id=excluded.repository_id, content_hash=excluded.content_hash, model=excluded.model, dimensions=excluded.dimensions, vector_json=excluded.vector_json, updated_at=excluded.updated_at""",
            (evidence_id, repository_id, content_hash, model, len(vector), json.dumps(vector), now()),
        )
        self.connection.commit()

    def put_decisions(self, decisions: list[dict[str, Any]], supersessions: list[dict[str, Any]]) -> None:
        self.connection.executemany(
            "INSERT INTO decisions(decision_id, repository_id, payload_json, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(decision_id) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at",
            [(decision["decision_id"], decision["repository_id"], json.dumps(decision, ensure_ascii=False), now()) for decision in decisions],
        )
        self.connection.executemany(
            "INSERT INTO supersession_assessments(assessment_id, repository_id, payload_json, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(assessment_id) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at",
            [(assessment["assessment_id"], assessment["repository_id"], json.dumps(assessment, ensure_ascii=False), now()) for assessment in supersessions],
        )
        self.connection.commit()

    def list_decisions(self, repository_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        decisions = [json.loads(row["payload_json"]) for row in self.connection.execute("SELECT payload_json FROM decisions WHERE repository_id = ? ORDER BY updated_at", (repository_id,))]
        supersessions = [json.loads(row["payload_json"]) for row in self.connection.execute("SELECT payload_json FROM supersession_assessments WHERE repository_id = ? ORDER BY updated_at", (repository_id,))]
        return decisions, supersessions

    @staticmethod
    def _repository(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["counts"] = json.loads(value.pop("counts_json")) if value.get("counts_json") else None
        return value
