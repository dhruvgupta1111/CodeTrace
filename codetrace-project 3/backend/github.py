from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import GitHubSource
from .url_validation import GitHubRepository


class GitHubApiError(RuntimeError):
    def __init__(self, message: str, code: str = "github_request_failed"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GitHubResponse:
    payload: Any
    headers: dict[str, str]


class GitHubClient:
    def __init__(self, token: str | None = None, page_size: int = 100, timeout_seconds: int = 120, request: Callable[..., GitHubResponse] | None = None):
        self.token = token
        self.page_size = min(page_size, 100)
        self.timeout_seconds = timeout_seconds
        self._request_fn = request or self._request

    def collect_sources(self, repository: GitHubRepository) -> tuple[list[GitHubSource], list[str]]:
        warnings: list[str] = []
        sources: list[GitHubSource] = []
        try:
            issues = self._paginate(f"repos/{repository.full_name}/issues", {"state": "all"})
            for item in issues:
                if "pull_request" in item:
                    source_type = "pull_request"
                else:
                    source_type = "issue"
                source = self._source(repository, item, source_type)
                sources.append(source)
                comments = self._paginate(f"issues/{repository.full_name}/issues/{item['number']}/comments", {})
                sources.extend(self._comment_sources(repository, source.source_id, item["number"], comments))
        except GitHubApiError as exc:
            warnings.append(exc.code)
        # GitHub Discussions require GraphQL and a separate permission scope; do not silently pretend REST issues contain them.
        warnings.append("discussions_not_fetched_rest_api")
        return sources, warnings

    def _paginate(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        while True:
            response = self._request_fn(path, {**params, "per_page": str(self.page_size), "page": str(page)})
            if not isinstance(response.payload, list):
                raise GitHubApiError("GitHub returned a malformed list response", "github_malformed_response")
            items.extend(response.payload)
            link = response.headers.get("link", "")
            if 'rel="next"' not in link:
                return items
            page += 1

    @staticmethod
    def _source(repository: GitHubRepository, item: dict[str, Any], source_type: str) -> GitHubSource:
        number = item.get("number")
        return GitHubSource(
            source_id=f"github:{repository.full_name}:{source_type}:{number}", source_type=source_type, title=item.get("title"), body=item.get("body"),
            author=(item.get("user") or {}).get("login"), observed_at=item.get("updated_at"), source_url=item.get("html_url"), number=number,
        )

    @staticmethod
    def _comment_sources(repository: GitHubRepository, parent_id: str, number: int, comments: list[dict[str, Any]]) -> list[GitHubSource]:
        return [GitHubSource(
            source_id=f"github:{repository.full_name}:comment:{comment.get('id')}", source_type="comment", body=comment.get("body"),
            author=(comment.get("user") or {}).get("login"), observed_at=comment.get("updated_at"), source_url=comment.get("html_url"),
            number=number, parent_source_id=parent_id,
        ) for comment in comments]

    def _request(self, path: str, params: dict[str, str]) -> GitHubResponse:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(f"https://api.github.com/{path}?{query}", headers={"Accept": "application/vnd.github+json", "User-Agent": "CodeTrace/0.1", **({"Authorization": f"Bearer {self.token}"} if self.token else {})})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return GitHubResponse(json.load(response), {key.lower(): value for key, value in response.headers.items()})
        except urllib.error.HTTPError as exc:
            if exc.code == 403 and (exc.headers.get("X-RateLimit-Remaining") == "0" or "rate limit" in str(exc).lower()):
                raise GitHubApiError("GitHub rate limit exceeded", "github_rate_limited") from exc
            if exc.code in (401, 403):
                raise GitHubApiError("GitHub API permission denied", "github_permission_denied") from exc
            if exc.code == 404:
                raise GitHubApiError("GitHub source was not found or is inaccessible", "github_source_not_found") from exc
            raise GitHubApiError("GitHub API request failed", "github_request_failed") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise GitHubApiError("GitHub API request timed out or failed", "github_network_failure") from exc
