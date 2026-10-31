from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .config import Settings
from .decision import extract_decisions
from .evidence import content_hash, normalize_commit, normalize_documentation, normalize_github_source
from .graph import GraphService
from .github import GitHubApiError, GitHubClient
from .git_history import GitHistory, GitLimits
from .models import IngestionJob, Repository, SyncResult
from .store import Store
from .url_validation import parse_github_url


class IngestionService:
    def __init__(self, settings: Settings, store: Store | None = None, git_history: GitHistory | None = None, github: GitHubClient | None = None, graph: GraphService | None = None):
        settings.ensure_directories()
        self.settings = settings
        self.store = store or Store(settings.data_dir / "codetrace.sqlite3")
        self.git_history = git_history or GitHistory(settings.repository_cache_dir, GitLimits(settings.max_commits, settings.max_diff_bytes, settings.ingestion_timeout_seconds))
        self.github = github or GitHubClient(settings.github_token, settings.github_page_size, settings.ingestion_timeout_seconds)
        self.graph = graph or GraphService.from_settings(settings)

    def register_repository(self, remote_url: str, default_branch: str | None = None) -> Repository:
        parsed = parse_github_url(remote_url)
        current = self.store.get_repository(parsed.repository_id)
        if current:
            if default_branch and current.get("default_branch") != default_branch:
                self.store.update_repository(parsed.repository_id, default_branch=default_branch)
            return Repository.model_validate(self.store.get_repository(parsed.repository_id))
        record = {
            "id": parsed.repository_id, "full_name": parsed.full_name, "remote_url": parsed.canonical_url,
            "default_branch": default_branch, "index_status": "not_indexed", "last_indexed_at": None, "last_sync_sha": None,
        }
        return Repository.model_validate(self.store.upsert_repository(record))

    def create_job(self, repository_id: str) -> IngestionJob:
        if not self.store.get_repository(repository_id):
            raise KeyError("repository_not_found")
        active = self.store.get_active_job(repository_id)
        if active:
            return IngestionJob.model_validate(active)
        return IngestionJob.model_validate(self.store.create_job(f"job_{uuid.uuid4().hex}", repository_id))

    def get_job(self, job_id: str) -> IngestionJob | None:
        value = self.store.get_job(job_id)
        return IngestionJob.model_validate(value) if value else None

    def run_job(self, job_id: str) -> None:
        job = self.store.get_job(job_id)
        if not job or job["status"] != "pending":
            return
        repository = self.store.get_repository(job["repository_id"])
        if not repository:
            self.store.update_job(job_id, status="failed", stage="validation", error={"code": "repository_not_found", "message": "Repository does not exist", "request_id": job_id})
            return
        self.store.update_job(job_id, status="running", stage="git_history", progress=None)
        self.store.update_repository(repository["id"], index_status="running")
        try:
            parsed = parse_github_url(repository["remote_url"])
            sync_sha, commits, git_warnings = self.git_history.sync(parsed, repository["id"], repository.get("last_sync_sha"))
            documents, documentation_warnings = self.git_history.documentation(parsed, repository["id"], self.settings.max_documents, self.settings.max_file_bytes)
            self.store.update_job(job_id, stage="github_sources")
            sources, github_warnings = self.github.collect_sources(parsed)
            commit_sources = [{"source_id": commit.source_id, "source_type": "commit", **commit.model_dump(mode="json")} for commit in commits]
            github_source_payloads = [source.model_dump(mode="json") for source in sources]
            raw_sources = commit_sources + github_source_payloads
            raw_sources.extend({"source_id": document.source_id, "source_type": "documentation", **document.model_dump(mode="json")} for document in documents)
            self.store.put_sources(repository["id"], raw_sources)
            evidence_records = []
            normalized_records = []
            normalization_warnings = []
            for commit in commits:
                record, warnings = normalize_commit(repository["id"], commit, max_diff_bytes=self.settings.max_diff_bytes)
                evidence_records.append(record.model_dump(mode="json"))
                normalized_records.append(record)
                normalization_warnings.extend(str(warning) for warning in warnings)
                self.store.put_raw_source(repository["id"], {"source_id": commit.source_id, "source_type": "commit", **commit.model_dump(mode="json")}, record.provenance.raw_source_ref, content_hash(commit.model_dump(mode="json")))
            for source in sources:
                record, warnings = normalize_github_source(repository["id"], source)
                evidence_records.append(record.model_dump(mode="json"))
                normalized_records.append(record)
                normalization_warnings.extend(str(warning) for warning in warnings)
                self.store.put_raw_source(repository["id"], source.model_dump(mode="json"), record.provenance.raw_source_ref, content_hash(source.model_dump(mode="json")))
            for document in documents:
                record, warnings = normalize_documentation(document)
                evidence_records.append(record.model_dump(mode="json"))
                normalized_records.append(record)
                normalization_warnings.extend(str(warning) for warning in warnings)
                self.store.put_raw_source(repository["id"], document.model_dump(mode="json"), record.provenance.raw_source_ref, content_hash(document.model_dump(mode="json")))
            self.store.put_evidence(evidence_records)
            decisions, supersessions, decision_warnings = extract_decisions(repository["id"], normalized_records)
            self.store.put_decisions([decision.model_dump(mode="json") for decision in decisions], [assessment.model_dump(mode="json") for assessment in supersessions])
            graph_warnings = self.graph.upsert_evidence(repository["id"], normalized_records, decisions, supersessions)
            counts = {"commits": len(commits), "github_sources": len(sources), "documentation": len(documents), "evidence": len(evidence_records), "decisions": len(decisions)}
            self.store.update_repository(repository["id"], index_status="indexed", last_indexed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), last_sync_sha=sync_sha, counts_json=counts)
            self.store.update_job(job_id, status="completed", stage="completed", progress=None)
            # Keep the result available for future evidence/graph stages without pretending it is already an answer.
            self._last_result = SyncResult(repository_id=repository["id"], sync_sha=sync_sha, commits=commits, github_sources=sources, warnings=git_warnings + documentation_warnings + github_warnings + normalization_warnings + decision_warnings + graph_warnings, counts=counts)
        except (GitHubApiError, Exception) as exc:
            code = getattr(exc, "code", None) or self._error_code(exc)
            self.store.update_repository(repository["id"], index_status="failed")
            self.store.update_job(job_id, status="failed", stage="failed", error={"code": code, "message": str(exc)[:500], "request_id": job_id})

    @staticmethod
    def _error_code(exc: Exception) -> str:
        message = str(exc).lower()
        if "timed out" in message:
            return "ingestion_timeout"
        if "limit" in message:
            return "ingestion_limit_exceeded"
        return "ingestion_failed"
