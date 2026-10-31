# Question understanding and retrieval

`backend/retrieval.py` is independent from Ollama answer generation. It turns a question into a small `QuestionPlan`, searches normalized evidence, traverses the repository graph when available, and returns a bounded `RetrievalResult`.

## Question plan

The current MVP detects:

- intent: `why`, `what_changed`, `current`, `support`, or `unknown`;
- explicit backtick references;
- file paths and common source filenames;
- uppercase configuration keys;
- function-like references such as `PaymentService.charge()`.

The API path supplies repository scope. Retrieval does not infer or switch repositories from question text.

## Ranking

Each hit includes a transparent, non-calibrated score made from:

- `entity_match` — explicit file/key/function match;
- `exact_match` — an explicit reference appears in the evidence;
- `keyword_match` — overlap with normalized question terms;
- `source_relevance` — issues, pull requests, discussions, and documentation are weighted above raw commits;
- `temporal_relevance` — a timestamp is available;
- `graph_relationship` — a bounded graph path reached the evidence.
- `semantic_similarity` — optional cosine similarity from Ollama embeddings; this is wording proximity, not causality or confidence.

These values rank retrieval candidates. They are not probabilities and do not establish answer correctness.

Semantic retrieval is disabled by default and documented separately in [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md). When enabled, it is merged by stable evidence ID with keyword and graph results; failures fall back to the deterministic paths.

## Graph contribution

Graph traversal starts from matched file/configuration/source labels and walks at most two relationships in the retrieval service. A file reference can therefore reach a modifying commit and a separately normalized issue or discussion that explicitly references the same path. Returned `GraphPath` objects preserve node IDs, labels, node types, and relationship types.

If Neo4j is unavailable, direct search still runs and the result includes `neo4j_unavailable`. It does not claim graph reasoning occurred.

## Limits and failure states

`CODETRACE_RETRIEVAL_RESULT_LIMIT` caps returned hits, and `CODETRACE_RETRIEVAL_CONTEXT_LIMIT` caps excerpt characters. Duplicate source IDs collapse to one evidence record. Empty direct and graph retrieval returns `status=insufficient`; text marked as contradictory or superseded returns `status=conflicting` for caller review.

