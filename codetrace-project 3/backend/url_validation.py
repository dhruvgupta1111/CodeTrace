from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlparse


class RepositoryUrlError(ValueError):
    pass


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str
    full_name: str
    canonical_url: str

    @property
    def repository_id(self) -> str:
        digest = hashlib.sha256(f"github:{self.full_name.lower()}".encode()).hexdigest()[:24]
        return f"repo_{digest}"


_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


def parse_github_url(value: str) -> GitHubRepository:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise RepositoryUrlError("Only public https://github.com/{owner}/{repo} URLs are supported")
    if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        raise RepositoryUrlError("Repository URL must not contain credentials, ports, queries, or fragments")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise RepositoryUrlError("Repository URL must contain exactly an owner and repository name")
    owner, name = parts
    if name.endswith(".git"):
        name = name[:-4]
    if not owner or not name or not _PART.fullmatch(owner) or not _PART.fullmatch(name):
        raise RepositoryUrlError("Repository owner and name contain unsupported characters")
    return GitHubRepository(owner=owner, name=name, full_name=f"{owner}/{name}", canonical_url=f"https://github.com/{owner}/{name}.git")
