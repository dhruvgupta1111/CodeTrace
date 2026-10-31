from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import GitCommit, RawDocumentation
from .url_validation import GitHubRepository


class IngestionLimitError(RuntimeError):
    pass


class GitOperationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitLimits:
    max_commits: int
    max_diff_bytes: int
    timeout_seconds: int


class GitHistory:
    def __init__(self, cache_dir: Path, limits: GitLimits):
        self.cache_dir = cache_dir
        self.limits = limits

    def sync(self, repository: GitHubRepository, repository_id: str, since_sha: str | None = None) -> tuple[str, list[GitCommit], list[str]]:
        destination = self.cache_dir / repository_id
        if destination.exists() and not (destination / ".git").is_dir():
            raise GitOperationError("Repository cache path is not a Git repository")
        if (destination / ".git").is_dir():
            self._run(["git", "-C", os.fspath(destination), "fetch", "--prune", "origin"], timeout=self.limits.timeout_seconds)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            self._run(["git", "clone", "--no-checkout", "--filter=blob:none", repository.canonical_url, os.fspath(destination)], timeout=self.limits.timeout_seconds)
        sha = self._run(["git", "-C", os.fspath(destination), "rev-parse", "HEAD"], timeout=self.limits.timeout_seconds).stdout.strip()
        # Inspect the checked-out default branch only. Scanning every remote ref is
        # needlessly expensive for large repositories and can exhaust the ingestion
        # timeout before any evidence is produced.
        log_args = ["git", "-C", os.fspath(destination), "log"]
        if since_sha:
            log_args.extend(["--not", since_sha])
        log_args.extend([f"-n{self.limits.max_commits}", "--date=iso-strict", "--format=COMMIT%x1f%H%x1f%aN%x1f%aE%x1f%aI%x1f%s", "--numstat"])
        log = self._run(
            log_args,
            timeout=self.limits.timeout_seconds,
        ).stdout
        commits = self._parse_log(log, repository, self.limits.max_diff_bytes)
        warnings = []
        if len(commits) == self.limits.max_commits:
            warnings.append("commit_limit_reached")
        return sha, commits, warnings

    def documentation(self, repository: GitHubRepository, repository_id: str, max_documents: int, max_file_bytes: int) -> tuple[list[RawDocumentation], list[str]]:
        """Read bounded text documentation from Git blobs without checking out or executing files."""
        destination = self.cache_dir / repository_id
        listing = self._run(["git", "-C", os.fspath(destination), "ls-tree", "-r", "--name-only", "HEAD"], timeout=self.limits.timeout_seconds).stdout
        candidates = [path for path in listing.splitlines() if self._is_documentation(path)]
        warnings = ["document_limit_reached"] if len(candidates) > max_documents else []
        documents: list[RawDocumentation] = []
        for path in candidates[:max_documents]:
            try:
                content = self._run(["git", "-C", os.fspath(destination), "show", f"HEAD:{path}"], timeout=self.limits.timeout_seconds).stdout
            except GitOperationError:
                warnings.append("documentation_read_failed")
                continue
            if len(content.encode("utf-8", "replace")) > max_file_bytes:
                warnings.append("documentation_file_limit_reached")
                continue
            documents.append(RawDocumentation(source_id=f"git-doc:{path}", repository_id=repository_id, path=path, title=Path(path).name, content=content, source_url=f"https://github.com/{repository.full_name}/blob/HEAD/{path}"))
        return documents, sorted(set(warnings))

    @staticmethod
    def _is_documentation(path: str) -> bool:
        lower = path.lower()
        name = Path(path).name.lower()
        return name.startswith("readme") or lower.startswith(("docs/", ".github/")) or lower.endswith((".md", ".mdx", ".rst", ".adoc"))

    def _parse_log(self, output: str, repository: GitHubRepository, max_bytes: int) -> list[GitCommit]:
        if len(output.encode()) > max_bytes:
            raise IngestionLimitError("diff metadata limit exceeded")
        commits: list[GitCommit] = []
        current: dict[str, object] | None = None
        for line in output.splitlines():
            if line.startswith("COMMIT\x1f"):
                if current:
                    commits.append(self._commit(current, repository))
                _, sha, author, email, authored_at, message = line.split("\x1f", 5)
                current = {"sha": sha, "author": author, "email": email, "authored_at": authored_at, "message": message, "paths": []}
            elif current is not None and line and "\t" in line:
                additions, deletions, path = line.split("\t", 2)
                paths = current["paths"]
                assert isinstance(paths, list)
                paths.append(path)
                if additions.isdigit() and deletions.isdigit():
                    current["additions"] = int(current.get("additions", 0)) + int(additions)
                    current["deletions"] = int(current.get("deletions", 0)) + int(deletions)
                current["changed_files"] = int(current.get("changed_files", 0)) + 1
        if current:
            commits.append(self._commit(current, repository))
        return commits

    @staticmethod
    def _commit(value: dict[str, object], repository: GitHubRepository) -> GitCommit:
        sha = str(value["sha"])
        paths = value["paths"]
        assert isinstance(paths, list)
        return GitCommit(
            source_id=f"git:{sha}", sha=sha, message=str(value["message"]), author_name=str(value["author"]),
            author_email=str(value["email"]) or None, authored_at=str(value["authored_at"]), changed_paths=[str(path) for path in paths],
            additions=int(value["additions"]) if "additions" in value else None,
            deletions=int(value["deletions"]) if "deletions" in value else None,
            changed_files=int(value["changed_files"]) if "changed_files" in value else None,
            source_url=f"https://github.com/{repository.full_name}/commit/{sha}",
        )

    @staticmethod
    def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout, env={"PATH": os.getenv("PATH", "")})
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError("git operation timed out") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "git operation failed").strip()[:500]
            raise GitOperationError(detail) from exc
