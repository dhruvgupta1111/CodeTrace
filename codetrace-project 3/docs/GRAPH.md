# CodeTrace graph subsystem

## Response contract

`GET /v1/repositories/{repository_id}/graph?node_type=file&depth=1&limit=100` returns `GraphResponse`:

- `nodes`: stable `id`, repository scope, `node_type`, display label, metadata, and source IDs.
- `edges`: stable `id`, source/target node IDs, `relationship_type`, evidence IDs, and relationship metadata.
- `available`: `false` with empty nodes/edges and `warnings=["neo4j_unavailable"]` when Neo4j is not configured or cannot be reached.
- `truncated`: true when a configured bound removed results.

The frontend never submits Cypher. Node types are allowlisted, traversal depth is capped at 3, result count is capped at 250, and Neo4j queries have a timeout.

## Storage

The Neo4j adapter uses a common `Entity` label with a unique `id`, `repository_id`, `node_type`, and metadata properties. Relationships use one parameterized `RELATES` type with a `relationship_type` property. This avoids interpolating user input into labels or relationship names while preserving the public graph vocabulary.

Ingestion creates repository, source, evidence, and file nodes from normalized evidence. It creates `CONTAINS`, `SUPPORTED_BY`, `REFERENCES`, `MODIFIED_BY`, and `DISCUSSED_IN` only when those facts are present in the normalized source. Decisions, incidents, configuration keys, functions, and people are not fabricated when extraction has not produced them.

## Temporal rule

The graph builder accepts explicit supersession links only. A confirmed link becomes `SUPERSEDES` and must carry evidence IDs. An uncertain candidate becomes `RELATED_TO` with metadata `{candidate_relationship: "SUPERSEDES", certainty: "uncertain"}`. Commit chronology alone never creates either edge.

## Testing

`InMemoryGraphStore` is the deterministic test double for idempotent upserts, repository isolation, filtering, and bounded responses. `Neo4jGraphStore` owns constraints, parameterized writes, and bounded read query templates. A live Neo4j instance is optional for local development.

