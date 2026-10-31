# Local development

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+ only when the FastAPI backend is introduced
- Git for local repository inspection

## Frontend

```bash
npm install
cp .env.example .env.local
npm run dev
```

The default `.env.example` keeps `VITE_USE_MOCKS=true`, so no GitHub token, Neo4j instance, or Ollama service is required for the current UI.

## Backend ingestion service

The ingestion API lives under `backend/` and stores only normalized repository/job metadata plus extracted history JSON until a graph store is added. It accepts public `https://github.com/{owner}/{repo}` URLs, never executes repository files, and uses a cache directory for repeat synchronization.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Set `CODETRACE_DATA_DIR` and `CODETRACE_REPOSITORY_CACHE_DIR` outside the repository when running locally if desired. `GITHUB_TOKEN` is optional for public repositories; it is read only by the backend and never returned to clients.

## Configuration

| Variable | Required now | Meaning |
| --- | --- | --- |
| `VITE_API_BASE_URL` | No | FastAPI base URL; default `http://localhost:8000/v1` |
| `VITE_USE_MOCKS` | No | `true` uses local demo data; use `false` only with a compatible backend |
| `CODETRACE_DATA_DIR` | No | SQLite/state directory; default `./.codetrace` |
| `CODETRACE_REPOSITORY_CACHE_DIR` | No | Git working-copy cache; default `$CODETRACE_DATA_DIR/repositories` |
| `GITHUB_TOKEN` | No | Optional GitHub token for higher API limits; never expose it as `VITE_*` |
| `CODETRACE_NEO4J_URI` | No | Optional Neo4j URI; when absent, graph API returns an empty unavailable response |
| `CODETRACE_NEO4J_USERNAME` | No | Neo4j username, used only by the backend |
| `CODETRACE_NEO4J_PASSWORD` | No | Neo4j password, used only by the backend |
| `CODETRACE_NEO4J_DATABASE` | No | Neo4j database name; default `neo4j` |
| `CODETRACE_MAX_COMMITS` | No | Maximum commits extracted per synchronization; default `5000` |
| `CODETRACE_MAX_DIFF_BYTES` | No | Maximum diff metadata bytes processed per synchronization; default `50000000` |
| `CODETRACE_MAX_FILE_BYTES` | No | Maximum file metadata size accepted from GitHub; default `1000000` |
| `CODETRACE_INGESTION_TIMEOUT_SECONDS` | No | Git/GitHub operation timeout; default `120` |
| `CODETRACE_OLLAMA_BASE_URL` | No | Ollama HTTP base URL; default `http://localhost:11434` |
| `CODETRACE_OLLAMA_MODEL` | No | Existing local Ollama model name; default `llama3.1:8b` |
| `CODETRACE_OLLAMA_TIMEOUT_SECONDS` | No | Per-request timeout; default `60` |
| `CODETRACE_OLLAMA_CONTEXT_LIMIT` | No | Maximum context tokens requested from Ollama; default `12000` |
| `CODETRACE_OLLAMA_MAX_OUTPUT_TOKENS` | No | Maximum generated output tokens; default `800` |
| `CODETRACE_SEMANTIC_SEARCH_ENABLED` | No | Enable optional Ollama embedding retrieval; default `false` |
| `CODETRACE_OLLAMA_EMBEDDING_MODEL` | No | Ollama embedding model; default `nomic-embed-text` |
| `CODETRACE_SEMANTIC_MAX_CANDIDATES` | No | Maximum evidence records scanned by the bounded semantic index; default `500` |
| `CODETRACE_SEMANTIC_MIN_SIMILARITY_PERCENT` | No | Minimum cosine similarity percentage; default `15` |
| `CODETRACE_RETRIEVAL_RESULT_LIMIT` | No | Maximum ranked evidence results; default `20` |
| `CODETRACE_RETRIEVAL_CONTEXT_LIMIT` | No | Maximum evidence excerpt characters sent to answer generation; default `12000` |
| `CODETRACE_CORS_ORIGINS` | No | Comma-separated browser origins allowed to call the API; defaults to local Vite origins |

Keep secrets in a local `.env`, document names and safe defaults here, and never expose provider credentials through `VITE_*` variables. CodeTrace does not call Ollama model-pull endpoints; the configured model must already exist locally.

## Checks

```bash
npm run build
```

There is currently no frontend test script and no backend test suite in the supplied project. Do not report pytest, Ruff, or live integration checks as passing until those components are added and run.

