# Evidence normalization

The ingestion service keeps two related records:

1. `raw_sources` contains the source payload as received from Git or GitHub. It is updated in place by `raw_source_ref` when an upstream source changes.
2. `evidence` contains a normalized, searchable projection. Its stable `evidence_id` is derived from `(repository_id, source_type, source_id)`, so re-ingestion updates the record instead of duplicating it.

The wire shape is `EvidenceRecord` in `backend/models.py` and the `Evidence` schema in [`contracts/api.yaml`](../contracts/api.yaml). The frontend mirror is `NormalizedEvidence` in `src/types/index.ts`.

## Semantics

- `excerpt_origin=original` means the text is copied from a commit message, issue/comment body, or documentation source. `derived` is reserved for future summaries.
- `interpretations` is empty for the current normalizer. Any future inference must be explicitly labeled `inferred` or `machine_extracted` and list `basis_evidence_ids`.
- `summary` is nullable and is not a rationale claim. A message such as “fix retry” remains exactly that message; the normalizer does not infer why the retry was introduced.
- `provenance.raw_source_ref` points to the raw payload. `content_hash` identifies the normalized input version.
- `source_url`, author, timestamps, and line ranges are nullable when the upstream data cannot establish them. No placeholder values are inserted.

## File changes

Unified diff parsing extracts conservative metadata only: path, previous path for renames, added/modified/deleted/binary/unknown status, measured additions/deletions when available, and new-file line ranges from hunk headers. Empty, binary, malformed, and oversized diffs produce partial metadata plus warnings; they never become invented code explanations.

The current Git log path supplies changed paths and numstat totals. Per-file line ranges require a patch payload and therefore remain empty when only commit metadata is available. Documentation files are normalized as original excerpts; code content is never executed.

