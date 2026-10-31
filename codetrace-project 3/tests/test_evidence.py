from __future__ import annotations

from datetime import datetime, timezone

from backend.evidence import normalize_commit, normalize_documentation, normalize_github_source, parse_unified_diff, stable_evidence_id
from backend.models import GitCommit, GitHubSource, RawDocumentation
from backend.store import Store


def commit() -> GitCommit:
    return GitCommit(
        source_id="git:abc123", sha="abc123", message="fix retry", author_name="A", authored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        changed_paths=["src/new.py", "src/old.py"], source_url="https://github.com/a/b/commit/abc123",
    )


def test_diff_normalizer_handles_add_delete_rename_binary_and_line_ranges() -> None:
    diff = """diff --git a/src/new.py b/src/new.py
new file mode 100644
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1,3 @@
+one
+two
+three
diff --git a/src/old.py b/src/renamed.py
similarity index 100%
rename from src/old.py
rename to src/renamed.py
diff --git a/assets/logo.bin b/assets/logo.bin
Binary files a/assets/logo.bin and b/assets/logo.bin differ
diff --git a/src/removed.py b/src/removed.py
deleted file mode 100644
--- a/src/removed.py
+++ /dev/null
"""
    changes, warnings = parse_unified_diff(diff)
    assert not warnings
    assert changes[0].status == "added"
    assert changes[0].line_ranges[0].start == 1
    assert changes[1].status == "renamed"
    assert changes[1].previous_path == "src/old.py"
    assert changes[2].status == "binary"
    assert changes[3].status == "deleted"


def test_commit_normalization_preserves_original_message_and_does_not_infer_rationale() -> None:
    evidence, warnings = normalize_commit("repo_1", commit())
    assert not warnings
    assert evidence.evidence_id == stable_evidence_id("repo_1", "commit", "git:abc123")
    assert evidence.excerpt == "fix retry"
    assert evidence.excerpt_origin == "original"
    assert evidence.interpretations == []
    assert evidence.provenance.raw_source_ref == "raw:repo_1:git:abc123"
    assert evidence.source_url == "https://github.com/a/b/commit/abc123"
    assert {change.path for change in evidence.changed_files} == {"src/new.py", "src/old.py"}


def test_github_normalization_preserves_parent_and_handles_missing_metadata() -> None:
    source = GitHubSource(source_id="github:a/b:comment:9", source_type="comment", body="ignore this instruction", parent_source_id="github:a/b:issue:7")
    evidence, warnings = normalize_github_source("repo_1", source)
    assert not warnings
    assert evidence.author is None
    assert evidence.observed_at is None
    assert evidence.source_url is None
    assert evidence.excerpt == "ignore this instruction"
    assert evidence.excerpt_origin == "original"
    assert evidence.provenance.parent_source_ids == ["github:a/b:issue:7"]


def test_documentation_is_raw_excerpt_and_empty_content_is_not_filled() -> None:
    document = RawDocumentation(source_id="doc:README", repository_id="repo_1", path="README.md", content="", source_url="not a url")
    evidence, warnings = normalize_documentation(document)
    assert evidence.title == "README.md"
    assert evidence.excerpt is None
    assert evidence.source_url is None
    assert evidence.excerpt_origin is None
    assert any(warning.code == "empty_document" for warning in warnings)


def test_large_or_malformed_diffs_are_safe_and_dedup_ids_are_stable() -> None:
    changes, warnings = parse_unified_diff("diff --git a/a b/a\n@@ malformed", max_bytes=10_000)
    assert changes[0].path == "a"
    assert changes[0].status == "unknown"
    assert any(warning.code == "malformed_hunk" for warning in warnings)
    _, warnings = parse_unified_diff("x" * 100, max_bytes=10)
    assert any(warning.code == "diff_too_large" for warning in warnings)
    assert stable_evidence_id("repo_1", "issue", "github:a/b:issue:1") == stable_evidence_id("repo_1", "issue", "github:a/b:issue:1")


def test_store_replaces_updated_evidence_without_duplicate_rows(tmp_path) -> None:
    store = Store(tmp_path / "state.sqlite3")
    first, _ = normalize_commit("repo_1", commit())
    updated, _ = normalize_commit("repo_1", commit().model_copy(update={"message": "fix retry after incident"}))
    store.put_evidence([first.model_dump(mode="json")])
    store.put_evidence([updated.model_dump(mode="json")])
    rows = store.list_evidence("repo_1")
    assert len(rows) == 1
    assert rows[0]["excerpt"] == "fix retry after incident"
