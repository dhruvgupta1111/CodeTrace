# Decision extraction and temporal reasoning

The decision layer converts normalized evidence into `DecisionCandidate` records. A candidate is not automatically a historical truth.

## Candidate rules

- Commit messages must contain decision/change or replacement language. A message such as `fix retry` is not enough.
- Pull requests, issues, discussions, documentation, incidents, and decision records may produce candidates from their original text, but the candidate keeps `evidence_kind=explicit|inferred` and the original evidence ID.
- A candidate statement is a bounded source statement, not an LLM-generated explanation.
- Affected paths and configuration keys are extracted only when present in changed-file metadata or source text.
- Missing timestamps remain null and produce `decision_missing_timestamp`; events are not ordered by ingestion time.
- Conflict markers keep a candidate in `conflicting` status.

## Supersession rules

An assessment is `confirmed` only when all of the following hold:

1. Both candidates affect the same path or configuration key.
2. Both have timestamps and the newer event is later.
3. The later source explicitly signals replacement or reversal (`revert`, `rollback`, `replace`, `supersede`, `restore`, `instead of`, or similar).
4. Neither candidate is marked conflicting.
5. Both supporting evidence IDs are preserved on the assessment.

Otherwise, the assessment is `uncertain` or omitted. A confirmed assessment becomes a graph `SUPERSEDES` edge. An uncertain assessment becomes `RELATED_TO` with candidate metadata. A newer unrelated commit creates no assessment.

These are acceptance rules for the available evidence, not proof that the historical explanation is complete. The API exposes the evidence IDs and rationale so a verifier or user can inspect the sources.

