# CodeTrace architecture

## Current state

The project has a Vite/React frontend and a small FastAPI service. The frontend still uses mock-backed service functions for the current demo views, while its API base is ready for the documented `/v1` contracts. The backend handles repository registration, cached Git synchronization, normalized evidence, retrieval, graph status, Ollama-backed answer generation, verification, and job status. Neo4j and Ollama remain optional runtime dependencies.

## Target shape

```text
GitHub/Git repository
        │
        ▼
Ingestion ──► Normalization ──► Graph construction ──► Neo4j
     │              │                    │
     └──────────────┴──────────────► evidence index (optional embeddings)
                                          │
Question ──► Retrieval ──► Reasoning ──► Verification ──► Answer + citations
                                          │
                              FastAPI contract boundary
                                          │
                              Vite/React frontend + Cytoscape
```

The preferred implementation stack is Next.js/TypeScript/Tailwind/Cytoscape for a future frontend migration, FastAPI/Python 3.11+/Pydantic for the backend, GitPython plus GitHub REST for history, Neo4j for relationships, and Ollama behind a dedicated backend adapter. The existing Vite frontend is retained for this hackathon prototype because replacing it would add risk without improving the contract boundary.

## Responsibilities and boundaries

| Boundary | Owns | Does not own |
| --- | --- | --- |
| Ingestion | Fetching repository refs and external artifacts; resumable job progress | Answer wording or graph semantics |
| Normalization | Stable IDs, timestamps, source metadata, excerpts, file/line metadata, provenance | Deciding whether a rationale is true |
| Graph construction | Nodes, typed edges, relationship provenance, supersession links | UI filtering or LLM prompting |
| Retrieval | Candidate evidence by entity, time, source, and semantic similarity | Inventing missing evidence |
| Reasoning | Drafting a claim from retrieved evidence | Treating model output as proof |
| Verification | Citation coverage, conflicts, current-vs-superseded checks | Hiding uncertainty |
| API | Authentication later, validation, error envelopes, pagination, serialization | Direct Git or Neo4j access from the browser |
| Frontend | Loading/error/empty states, source inspection, graph/timeline interactions | Reimplementing ingestion or evidence scoring |

## Evidence and answer policy

Evidence strength is `strong`, `partial`, `insufficient`, or `conflicting`. Answer status is intentionally separate:

- `supported`: the answer is backed by relevant, non-conflicting evidence.
- `partially_supported`: some rationale is supported, but important links or verification are missing.
- `insufficient`: no evidence supports a reliable explanation; the answer must say so.
- `conflicting`: sources disagree or supersession cannot be resolved; surface both sides.

The verifier should return citations and conflict details with every non-empty answer. An LLM may summarize evidence, but it may not create a source, URL, commit, decision, or confidence claim that was not retrieved.

## Hackathon sequencing

1. Keep the existing UI and canonical contracts stable.
2. Run the real-mode frontend against the FastAPI service with `VITE_USE_MOCKS=false`.
3. Add local Git ingestion and normalized evidence before optional Neo4j/Ollama services.
4. Keep Neo4j, Ollama, and embeddings behind adapters with explicit unavailable states.
5. Expand the labelled evaluation set with repository-specific fixtures before making quality claims.

