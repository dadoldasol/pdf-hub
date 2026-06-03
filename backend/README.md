# PDF Knowledge Hub Backend

FastAPI backend for the PDF Knowledge Hub MVP.

## What Works

- PDF upload and local file storage
- Processing job creation and status lookup
- Page-level text extraction with PyMuPDF
- Chunk creation
- Deterministic local embeddings for MVP development
- pgvector-based vector search
- Rule/pattern-based entity extraction
- Entity mentions with source page/snippet
- Knowledge card API
- Co-mention graph API

## Local Setup

From the project root, start PostgreSQL + pgvector:

```powershell
docker compose up -d postgres
```

Create backend environment:

```powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
```

If `python` is not available on Windows, use an installed Python launcher or the project-specific Python executable available in your environment.

## Run Server

From the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If the backend was already running, stop it with `Ctrl+C` in that terminal and run the command again.

Useful URLs:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

## Run Frontend

From the project root:

```powershell
node frontend\server.js
```

Open:

```text
http://127.0.0.1:5173
```

## Main API Flow

```text
POST /api/documents/upload
GET  /api/jobs/{job_id}
POST /api/jobs/{job_id}/cancel
GET  /api/documents
GET  /api/documents/{document_id}
GET  /api/documents/{document_id}/pages/{page_number}
POST /api/search
GET  /api/entities
GET  /api/entities/{entity_id}
GET  /api/entities/{entity_id}/knowledge-card
GET  /api/graph/entities/{entity_id}
```

## Checks

```powershell
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\ruff.exe check app tests
```

## Current MVP Limits

- Embeddings are deterministic local vectors, not production semantic embeddings.
- Entity extraction is rule/pattern-based.
- OCR, table extraction, LLM summarization, and advanced relation extraction are deferred.
- Graph edges are generated dynamically from co-mentions rather than persisted as inferred relations.
