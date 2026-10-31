from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .models import EvidenceRecord, FileChange, GitCommit, GitHubSource, LineRange, Provenance, RawDocumentation


NORMALIZER_VERSION = "evidence-v1"
_HUNK = re.compile(r"@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@")


class NormalizationWarning:
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


def parse_unified_diff(diff: str | None, max_bytes: int = 1_000_000) -> tuple[list[FileChange], list[NormalizationWarning]]:
    """Extract conservative file/line metadata from a unified diff, never code meaning."""
    if not diff:
        return [], []
    if len(diff.encode("utf-8", "replace")) > max_bytes:
        return [], [NormalizationWarning("diff_too_large", "diff exceeded the configured normalization limit")]
    changes: list[FileChange] = []
    warnings: list[NormalizationWarning] = []
    current: dict[str, Any] | None = None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            if current:
                changes.append(FileChange.model_validate(current))
            parts = line.split(" ", 3)
            path = _strip_diff_prefix(parts[3]) if len(parts) == 4 else ""
            current = {"path": path, "status": "unknown", "line_ranges": []}
            continue
        if current is None:
            continue
        if line.startswith("new file mode"):
            current["status"] = "added"
        elif line.startswith("deleted file mode"):
            current["status"] = "deleted"
        elif line.startswith("rename from "):
            current["previous_path"] = line.removeprefix("rename from ")
            current["status"] = "renamed"
        elif line.startswith("rename to "):
            current["path"] = line.removeprefix("rename to ")
            current["status"] = "renamed"
        elif line.startswith("Binary files ") or line == "GIT binary patch":
            current["status"] = "binary"
        elif line.startswith("+++ "):
            path = line[4:]
            if path == "/dev/null":
                current["status"] = "deleted"
            else:
                current["path"] = _strip_diff_prefix(path)
                if current["status"] == "unknown":
                    current["status"] = "modified"
        elif line.startswith("--- ") and line[4:] != "/dev/null" and not current.get("previous_path"):
            current["previous_path"] = _strip_diff_prefix(line[4:])
        elif line.startswith("@@ "):
            match = _HUNK.search(line)
            if match and int(match.group("new_count") or "1") > 0:
                start = int(match.group("new_start"))
                end = start + int(match.group("new_count") or "1") - 1
                current["line_ranges"].append(LineRange(start=start, end=end))
            elif not match:
                warnings.append(NormalizationWarning("malformed_hunk", line[:120]))
    if current:
        changes.append(FileChange.model_validate(current))
    changes = [change for change in changes if change.path]
    return changes, warnings


def normalize_commit(repository_id: str, commit: GitCommit, diff: str | None = None, max_diff_bytes: int = 1_000_000) -> tuple[EvidenceRecord, list[NormalizationWarning]]:
    file_changes, warnings = parse_unified_diff(diff, max_diff_bytes)
    if not file_changes:
        file_changes = [FileChange(path=path, status="unknown") for path in commit.changed_paths]
    else:
        _merge_numstat(file_changes, commit)
    now = datetime.now(timezone.utc)
    evidence_id = stable_evidence_id(repository_id, "commit", commit.source_id)
    record = EvidenceRecord(
        evidence_id=evidence_id, repository_id=repository_id, source_type="commit", source_id=commit.source_id,
        title=commit.message.splitlines()[0][:200] if commit.message else None, summary=commit.message or None,
        author=commit.author_name or None, observed_at=commit.authored_at, source_url=validated_url(commit.source_url),
        excerpt=commit.message or None, excerpt_origin="original" if commit.message else None, changed_files=file_changes,
        provenance=Provenance(source_type="commit", source_id=commit.source_id, repository_id=repository_id, raw_source_ref=f"raw:{repository_id}:{commit.source_id}", ingested_at=now, normalizer_version=NORMALIZER_VERSION),
        content_hash=content_hash(commit.model_dump(mode="json")),
    )
    return record, warnings


def normalize_github_source(repository_id: str, source: GitHubSource) -> tuple[EvidenceRecord, list[NormalizationWarning]]:
    now = datetime.now(timezone.utc)
    warnings: list[NormalizationWarning] = []
    url = validated_url(source.source_url)
    if source.source_url and not url:
        warnings.append(NormalizationWarning("invalid_source_url", source.source_id))
    body = source.body or None
    record = EvidenceRecord(
        evidence_id=stable_evidence_id(repository_id, source.source_type, source.source_id), repository_id=repository_id,
        source_type=source.source_type, source_id=source.source_id, title=source.title, summary=None,
        author=source.author or None, observed_at=source.observed_at, source_url=url, excerpt=body, excerpt_origin="original" if body else None,
        provenance=Provenance(source_type=source.source_type, source_id=source.source_id, repository_id=repository_id, raw_source_ref=f"raw:{repository_id}:{source.source_id}", ingested_at=now, normalizer_version=NORMALIZER_VERSION, parent_source_ids=[source.parent_source_id] if source.parent_source_id else []),
        content_hash=content_hash(source.model_dump(mode="json")),
    )
    return record, warnings


def normalize_documentation(document: RawDocumentation) -> tuple[EvidenceRecord, list[NormalizationWarning]]:
    now = datetime.now(timezone.utc)
    title = document.title or document.path.rsplit("/", 1)[-1] or None
    excerpt = document.content[:4000] if document.content else None
    warnings = [] if document.content else [NormalizationWarning("empty_document", document.path)]
    record = EvidenceRecord(
        evidence_id=stable_evidence_id(document.repository_id, "documentation", document.source_id), repository_id=document.repository_id,
        source_type="documentation", source_id=document.source_id, title=title, summary=None, author=document.author or None,
        observed_at=document.observed_at, source_url=validated_url(document.source_url), excerpt=excerpt, excerpt_origin="original" if excerpt else None,
        provenance=Provenance(source_type="documentation", source_id=document.source_id, repository_id=document.repository_id, raw_source_ref=f"raw:{document.repository_id}:{document.source_id}", ingested_at=now, normalizer_version=NORMALIZER_VERSION),
        content_hash=content_hash(document.model_dump(mode="json")),
    )
    return record, warnings


def stable_evidence_id(repository_id: str, source_type: str, source_id: str) -> str:
    digest = hashlib.sha256(f"{repository_id}\x1f{source_type}\x1f{source_id}".encode()).hexdigest()[:32]
    return f"evidence_{digest}"


def content_hash(value: dict[str, Any]) -> str:
    import json
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8", "replace")
    return hashlib.sha256(encoded).hexdigest()


def validated_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return None
    return value


def _strip_diff_prefix(path: str) -> str:
    return path[2:] if path.startswith(("a/", "b/")) else path


def _merge_numstat(changes: list[FileChange], commit: GitCommit) -> None:
    for change in changes:
        if change.path in commit.changed_paths and len(changes) == 1:
            change.additions = commit.additions
            change.deletions = commit.deletions
