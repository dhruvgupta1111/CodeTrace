from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.github import GitHubApiError, GitHubClient, GitHubResponse
from backend.git_history import GitHistory, GitLimits
from backend.service import IngestionService
from backend.url_validation import RepositoryUrlError, parse_github_url


def test_github_url_validation_accepts_only_public_repository_urls() -> None:
    parsed = parse_github_url("https://github.com/Acme/Payments.git")
    assert parsed.full_name == "Acme/Payments"
    assert parsed.canonical_url == "https://github.com/Acme/Payments.git"
    assert parsed.repository_id.startswith("repo_")
    for value in ("http://github.com/a/b", "https://example.com/a/b", "https://github.com/a", "https://github.com/a/b?x=1"):
        with pytest.raises(RepositoryUrlError):
            parse_github_url(value)


def test_github_client_follows_pagination_and_keeps_stable_source_ids() -> None:
    calls: list[int] = []

    def request(path: str, params: dict[str, str]) -> GitHubResponse:
        calls.append(int(params["page"]))
        if path.endswith("/comments"):
            return GitHubResponse([], {})
        if params["page"] == "1":
            return GitHubResponse([{"number": 7, "title": "Why", "body": "context", "user": {"login": "a"}, "updated_at": "2026-01-01T00:00:00Z", "html_url": "https://github.com/a/b/issues/7"}], {"link": '<https://api.github.com/?page=2>; rel="next"'})
        return GitHubResponse([], {})

    client = GitHubClient(request=request)
    sources, warnings = client.collect_sources(parse_github_url("https://github.com/a/b"))
    assert calls == [1, 2, 1]
    assert sources[0].source_id == "github:a/b:issue:7"
    assert "discussions_not_fetched_rest_api" in warnings


def test_github_client_surfaces_rate_limits_and_malformed_responses() -> None:
    def limited(path: str, params: dict[str, str]) -> GitHubResponse:
        raise GitHubApiError("limited", "github_rate_limited")

    sources, warnings = GitHubClient(request=limited).collect_sources(parse_github_url("https://github.com/a/b"))
    assert sources == []
    assert "github_rate_limited" in warnings

    def malformed(path: str, params: dict[str, str]) -> GitHubResponse:
        return GitHubResponse({"not": "a list"}, {})

    sources, warnings = GitHubClient(request=malformed).collect_sources(parse_github_url("https://github.com/a/b"))
    assert sources == []
    assert "github_malformed_response" in warnings


def test_repeated_registration_and_active_ingestion_are_idempotent(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", repository_cache_dir=tmp_path / "repos", github_token=None)
    service = IngestionService(settings)
    first = service.register_repository("https://github.com/a/b")
    second = service.register_repository("https://github.com/a/b.git")
    assert first.id == second.id
    assert service.create_job(first.id).id == service.create_job(first.id).id

    service.store.put_sources(first.id, [{"source_id": "git:abc", "source_type": "commit", "message": "one"}])
    service.store.put_sources(first.id, [{"source_id": "git:abc", "source_type": "commit", "message": "updated"}])
    count = service.store.connection.execute("SELECT count(*) FROM sources WHERE repository_id = ?", (first.id,)).fetchone()[0]
    assert count == 1


def test_git_log_parser_extracts_metadata_without_executing_repository_code(tmp_path: Path) -> None:
    history = GitHistory(tmp_path, GitLimits(10, 10_000, 1))
    output = "COMMIT\x1fabc123\x1fAuthor\x1fa@example.com\x1f2026-01-01T00:00:00+00:00\x1fAdd policy\n2\t1\tsrc/policy.py\n4\t0\tdocs/adr.md\n"
    commits = history._parse_log(output, parse_github_url("https://github.com/a/b"), 10_000)
    assert commits[0].sha == "abc123"
    assert commits[0].changed_paths == ["src/policy.py", "docs/adr.md"]
    assert commits[0].additions == 6
    assert commits[0].deletions == 1
    assert commits[0].changed_files == 2


def test_api_returns_structured_url_errors_and_repository_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend import app as app_module

    settings = Settings(data_dir=tmp_path / "data", repository_cache_dir=tmp_path / "repos", github_token=None)
    monkeypatch.setattr(app_module, "service", IngestionService(settings))
    client = TestClient(app_module.app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "dependencies" in health.json()
    invalid = client.post("/v1/repositories", json={"remote_url": "https://example.com/a/b"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_repository_url"
    created = client.post("/v1/repositories", json={"remote_url": "https://github.com/a/b"})
    assert created.status_code == 201
    assert created.json()["index_status"] == "not_indexed"
    invalid_id = client.get("/v1/repositories/not-a-repository")
    assert invalid_id.status_code == 422
    assert invalid_id.json()["error"]["code"] == "invalid_repository_id"
