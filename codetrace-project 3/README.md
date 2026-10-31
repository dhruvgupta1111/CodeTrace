# CodeTrace

CodeTrace is a hackathon application for T1.1, “Why The Code Is Like This?”. It explains code and configuration by connecting repository history to traceable evidence from commits, documentation, issues, pull requests, and comments.

## Features

- Connect public GitHub repositories and synchronize Git history.
- Extract commit authors, timestamps, changed paths, additions, deletions, and diff metadata.
- Extract bounded README, Markdown, MDX, RST, AsciiDoc, `docs/`, and `.github/` documentation.
- Fetch GitHub issues, pull requests, and comments when API access is available.
- Normalize sources into stable evidence records with provenance and source URLs.
- Explore evidence, candidate decisions, timelines, and graph relationships.
- Ask natural-language questions and receive evidence-grounded answers through Ollama.
- Validate citations and abstain when evidence is insufficient or conflicting.
- Optional Neo4j graph storage and Ollama semantic retrieval.
- Responsive dashboard, repository switching, sync controls, account UI, themes, loading states, and honest empty/error states.

## Architecture

```text
React + TypeScript + Tailwind + Cytoscape
                 |
             FastAPI API
                 |
 ingestion -> normalization -> retrieval -> verification
       |              |             |             |
     Git          SQLite        Neo4j optional  Ollama optional
   GitHub API
```

Frontend code is in `src/`; backend code is in `backend/`. Contracts and design notes are in `contracts/` and `docs/`.

## Run locally

### Frontend

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

For real backend data, create `.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/v1
VITE_USE_MOCKS=false
```

### Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

The API is under `http://127.0.0.1:8000/v1`.

For larger ingestion runs:

```bash
CODETRACE_INGESTION_TIMEOUT_SECONDS=600 \
CODETRACE_MAX_COMMITS=1000 \
CODETRACE_MAX_DOCUMENTS=100 \
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

## Configuration

Start from `.env.example`. Important variables include:

- `CODETRACE_DATA_DIR` and `CODETRACE_REPOSITORY_CACHE_DIR` for local storage.
- `GITHUB_TOKEN` for higher GitHub API limits; it remains server-side.
- `CODETRACE_MAX_COMMITS`, `CODETRACE_MAX_DOCUMENTS`, `CODETRACE_MAX_FILE_BYTES`, and `CODETRACE_MAX_DIFF_BYTES` for ingestion bounds.
- `CODETRACE_INGESTION_TIMEOUT_SECONDS` for Git/GitHub time limits.
- `CODETRACE_NEO4J_URI`, `CODETRACE_NEO4J_USERNAME`, and `CODETRACE_NEO4J_PASSWORD` for optional Neo4j.
- `CODETRACE_OLLAMA_BASE_URL`, `CODETRACE_OLLAMA_MODEL`, and `CODETRACE_OLLAMA_TIMEOUT_SECONDS` for answer generation.
- `CODETRACE_SEMANTIC_SEARCH_ENABLED` and `CODETRACE_OLLAMA_EMBEDDING_MODEL` for optional embeddings.

Never commit `.env.local`, credentials, tokens, or private repository data.

## API workflow

1. `POST /v1/repositories` registers a repository.
2. `POST /v1/repositories/{id}/ingestion-jobs` starts synchronization.
3. `GET /v1/repositories/{id}` returns status and genuine counts.
4. `GET /v1/repositories/{id}/evidence` lists normalized evidence.
5. `GET /v1/repositories/{id}/decisions` lists candidate decisions.
6. `GET /v1/repositories/{id}/graph` returns bounded graph data.
7. `POST /v1/repositories/{id}/questions` retrieves evidence, calls Ollama, and verifies citations.

Answer statuses are `supported`, `partially_supported`, `insufficient_evidence`, and `conflicting_evidence`.

## Checks

```bash
npm run build
ruff check backend tests
pytest -q
python3 -m compileall -q backend
```

## Authentication note

The current Login/Create Account screens and Settings account controls provide a local browser session for the demo. Server-side authentication, password storage, OAuth, and multi-user authorization are not implemented yet.

## Known limitations

- GitHub Discussions are not fetched by the current REST-only client.
- Neo4j and Ollama are optional and report controlled unavailable states when not configured.
- File-content indexing is limited compared with commit and documentation evidence.
- Semantic similarity does not prove causality.
- Candidate decisions remain distinct from original historical facts.
- The frontend build has a known Vite chunk-size warning.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API contracts](docs/API_CONTRACTS.md)
- [Local development](docs/LOCAL_DEVELOPMENT.md)
- [Evidence normalization](docs/EVIDENCE_NORMALIZATION.md)
- [Graph design](docs/GRAPH.md)
- [Retrieval](docs/RETRIEVAL.md)
- [Decision reasoning](docs/DECISIONS.md)
- [Ollama](docs/OLLAMA.md)
- [Verification](docs/VERIFICATION.md)
- [Semantic search](docs/SEMANTIC_SEARCH.md)
