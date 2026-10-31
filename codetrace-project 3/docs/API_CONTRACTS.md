# API and frontend contracts

The canonical wire format is [`contracts/api.yaml`](../contracts/api.yaml). This document explains the rules that are easy to miss when implementing either side.

## Conventions

- IDs are opaque strings scoped by resource type (for example, `repo_...`, `evidence_...`, `job_...`). Clients must not parse them.
- All timestamps are RFC 3339 UTC strings with an explicit `Z` suffix. A date-only value is used only for display filters, never for event timestamps.
- `source_type` is one of `commit`, `pull_request`, `issue`, `discussion`, `documentation`, `incident`, `code_excerpt`, or `decision_record`.
- Every source-linked item has a stable `source_url` when the upstream system provides one, plus a human-readable excerpt and provenance.
- Normalized evidence keeps `excerpt_origin=original|derived`; summaries and interpretations are never substitutes for the raw source. Interpretations must name their basis evidence IDs.
- `provenance.raw_source_ref` points to the stored raw payload, while `content_hash` lets updates replace an existing source without creating duplicates.
- Lists are returned as `{items, next_cursor}`. An omitted cursor means there is no next page.
- Errors use `{error: {code, message, request_id, details}}`. `message` is safe to show; `details` is for structured field or provider diagnostics.

## Frontend expectations

The frontend must be able to:

- show ingestion job state (`pending`, `running`, `completed`, `failed`, `cancelled`) and progress without polling assumptions; progress is nullable and must not be fabricated;
- ask a question and render `supported`, `partially_supported`, `insufficient_evidence`, or `conflicting_evidence` honestly;
- link every answer claim to one or more evidence IDs and let the user inspect the evidence;
- inspect retrieval independently through `POST /v1/repositories/{repository_id}/retrieval`; ranking scores are transparent signals, not calibrated correctness probabilities;
- distinguish current, superseded, and unresolved decisions in a timeline;
- distinguish confirmed, uncertain, unresolved, and conflicting decision candidates through `GET /v1/repositories/{repository_id}/decisions`;
- inspect trusted answer sources and verification warnings through the `verification` and `warnings` fields on answer responses;
- render graph nodes/edges even when optional descriptions or URLs are absent;
- show empty data, loading, and retryable error states rather than treating empty results as failures.

## Endpoint plan

The OpenAPI file documents the boundary. In this checkout repository registration, ingestion jobs, evidence, retrieval, decisions, graph status, and question orchestration are implemented by FastAPI; timeline and final frontend data wiring remain future work, and the frontend still uses mocks for those views.

The canonical runtime prefix is `/v1`; the frontend default is configured to use `http://localhost:8000/v1`. `/health` and `/api/health` are both available for local health checks. The backend allows only the configured local browser origins and never returns provider credentials.

| Operation | Purpose | Current implementation |
| --- | --- | --- |
| `GET /v1/repositories` | List connected repositories | FastAPI implemented |
| `POST /v1/repositories` | Register a repository | FastAPI implemented |
| `POST /v1/repositories/{repository_id}/ingestion-jobs` | Start ingestion | FastAPI implemented |
| `GET /v1/ingestion-jobs/{job_id}` | Read progress | FastAPI implemented |
| `POST /v1/repositories/{repository_id}/questions` | Retrieve evidence and generate an answer | FastAPI implemented; Ollama required for non-empty retrieval |
| `POST /v1/repositories/{repository_id}/retrieval` | Retrieve ranked evidence and graph context | FastAPI implemented |
| `GET /v1/repositories/{repository_id}/evidence` | Browse normalized evidence | FastAPI implemented |
| `GET /v1/repositories/{repository_id}/decisions` | Browse decision candidates and supersession assessments | FastAPI implemented |
| `GET /v1/repositories/{repository_id}/graph` | Explore bounded graph | FastAPI implemented; Neo4j unavailable is explicit |
| `GET /v1/repositories/{repository_id}/timeline` | Inspect decisions over time | Mock only |

Equivalent frontend operation mapping:

- repository connection: `POST /v1/repositories` with `{ "remote_url": "https://github.com/owner/name", "default_branch": "main" }`; returns `201` and a `repo_<24 hex>` ID;
- sync: `POST /v1/repositories/{repository_id}/ingestion-jobs`; returns `202` with `status=pending|running|completed|failed|cancelled` and nullable `progress`;
- question: `POST /v1/repositories/{repository_id}/questions` with `{ "question": "Why is ...?", "entity_ids": [] }`; returns `Answer.status` as `supported|partially_supported|insufficient_evidence|conflicting_evidence`;
- graph: `GET /v1/repositories/{repository_id}/graph?depth=1&limit=100`; depth is bounded to `0..3`, limit to `1..250`;
- safe errors: `{ "error": { "code": "...", "message": "...", "request_id": "...", "details": {} } }` for validation, missing resources, provider failures, and ingestion failures.

The health response is `{ "status": "ok", "dependencies": { "database": "ok", "neo4j": "configured|unconfigured", "ollama": "not_checked" } }`. This endpoint does not make live provider calls; `configured` means settings are present, not that the provider is reachable. Empty evidence, graph, or decision lists return `items: []` (and graph responses return `nodes: []`, `edges: []`) rather than fabricated data.

