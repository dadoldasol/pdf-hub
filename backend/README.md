# PDF Knowledge Hub Backend

FastAPI backend for the PDF Knowledge Hub MVP.

## What Works

- PDF upload and local file storage
- Duplicate PDF upload detection by SHA-256 file hash
- Document deletion with local file and document-scoped data cleanup
- Processing job creation and status lookup
- Page-level text extraction with PyMuPDF in a timeout-isolated child process
- Partial processing when individual pages time out or fail
- Chunk creation
- Deterministic local embeddings for MVP development
- pgvector-based vector search
- Rule/pattern-based entity extraction
- Automatic post-ingestion LLM refinement jobs for entity descriptions and knowledge cards
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

## Run Dev Services

From the project root, start the backend API, ingestion worker, and frontend together.

Windows PowerShell:

```powershell
.\scripts\dev.cmd start
```

Ubuntu/bash:

```bash
bash scripts/dev.sh start
```

To also start the local PostgreSQL container, add the PostgreSQL flag.

Windows PowerShell:

```powershell
.\scripts\dev.cmd start --with-postgres
```

Ubuntu/bash:

```bash
bash scripts/dev.sh start --with-postgres
```

Useful commands:

```powershell
.\scripts\dev.cmd status
.\scripts\dev.cmd logs
.\scripts\dev.cmd restart
.\scripts\dev.cmd stop
```

```bash
bash scripts/dev.sh status
bash scripts/dev.sh logs
bash scripts/dev.sh restart
bash scripts/dev.sh stop
```

The script writes process IDs and logs under `.dev/`, which is ignored by Git.

## Run Server Manually

From the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If the backend was already running, stop it with `Ctrl+C` in that terminal and run the command again.

Uploads create queued processing jobs. Run the ingestion worker in a second terminal to process them:

```powershell
.\.venv\Scripts\python.exe -m app.workers.worker_main
```

For a one-shot local check, process at most one queued job and exit:

```powershell
.\.venv\Scripts\python.exe -m app.workers.worker_main --once
```

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

## LLM Refinement

Upload ingestion stores rule/pattern entities only so PDF processing remains stable. After ingestion completes, the worker automatically queues a separate `llm_refinement` job for the same document. That refinement job can use an LLM to improve entity descriptions and knowledge card summaries without blocking upload ingestion.

To manually queue refinement for an existing document:

```text
POST /api/documents/{document_id}/refine
```

If a refinement job is already queued or running, the existing job is returned. If the latest refinement already finished, pass `{"force": true}` to queue a new refinement job.

For local Ollama refinement, set:

```env
ENABLE_LLM_ENTITY_VALIDATION=true
LLM_PROVIDER=ollama
ENTITY_VALIDATION_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=ollama
```

For local Ollama, install and pull the recommended 8B model:

```powershell
ollama pull qwen3:8b
ollama run qwen3:8b
```

`OPENAI_API_KEY` is ignored by Ollama, but can remain set to `ollama` for compatibility. To use OpenAI instead:

```env
ENABLE_LLM_ENTITY_VALIDATION=true
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
ENTITY_VALIDATION_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

## Main API Flow

```text
POST /api/documents/upload
GET  /api/jobs/{job_id}
POST /api/jobs/{job_id}/cancel
GET  /api/documents
GET  /api/documents/{document_id}
GET  /api/documents/{document_id}/pages/{page_number}
DELETE /api/documents/{document_id}
POST /api/documents/{document_id}/refine
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
- Entity extraction starts with rule/pattern candidates; LLM refinement runs afterward as a separate worker job.
- Upload ingestion does not call the LLM, which protects large PDF processing stability.
- OCR, table extraction, LLM summarization, and advanced relation extraction are deferred.
- Graph edges are generated dynamically from co-mentions rather than persisted as inferred relations.
