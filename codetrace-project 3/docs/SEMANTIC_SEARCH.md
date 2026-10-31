# Optional semantic retrieval

Keyword matching plus graph traversal is the default MVP path because it is deterministic, cheap, and available without Ollama. Semantic retrieval is useful when a question uses different wording from the historical source (for example, “protect upstream rate limits” versus “bounded retries”). It is therefore an optional recall improvement, not a causal signal or answer-confidence score.

Set `CODETRACE_SEMANTIC_SEARCH_ENABLED=true` and provide the embedding model in `CODETRACE_OLLAMA_EMBEDDING_MODEL`. CodeTrace calls Ollama's `/api/embed` endpoint only when retrieval runs; it never downloads a model at startup. The embedding cache is stored in SQLite with the stable evidence ID, source content hash, model, dimensions, and vector. Unchanged evidence reuses its vector; a changed content hash regenerates it.

For the hackathon-sized index, vectors are scanned in a bounded in-process index. A separate vector database is not justified yet. Results are merged with exact, keyword, and graph matches, deduplicated by evidence ID, and returned in the same evidence format. If embeddings fail, retrieval records a controlled warning and continues with keyword-plus-graph retrieval.

Semantic similarity indicates wording proximity only. It does not prove that a source explains why code exists, and it is never treated as answer confidence.
