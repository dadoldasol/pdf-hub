# 2026-06-03 Document Lifecycle

## Session Summary

MVP end-to-end flow had already been verified. After entity validation work was committed and pushed, this session addressed a new operational gap: uploaded documents stayed forever and uploading the same PDF again duplicated the same content in the knowledge store.

This session designed and implemented the first document lifecycle improvements:

- duplicate upload detection by PDF content hash
- document deletion API
- document-scoped cleanup
- frontend delete action and duplicate upload notice
- documentation updates for API, data model, ingestion, UI, and implementation plan

The document lifecycle changes are implemented and validated locally, but they are not committed yet at the time of this handoff.

## Current Project State

- Branch: `main`
- Remote status before this handoff: `main...origin/main`
- Latest pushed commit: `afcb9e6 feat: add LLM-backed entity validation`
- Working tree has uncommitted document lifecycle changes.
- Local DB migration `20260603_0002_document_file_hash` was applied successfully with `alembic upgrade head`.
- Existing `docs/history/2026-06-03-cancellable-ingestion.md` remains untracked from a previous session and is intentionally not part of this lifecycle work.
- `backend/.pytest_cache/` still produces a permission warning during `git status`, but cache files are not part of the intended changes.

## Completed Work

### Documentation

Updated lifecycle design in:

- `docs/backend/api-design.md`
- `docs/backend/data-model.md`
- `docs/backend/ingestion-pipeline.md`
- `docs/frontend/ui-requirements.md`
- `docs/implementation-plan.md`

Documented these policies:

- upload -> deduplicate -> process -> list/search -> delete -> future reprocess
- duplicate detection is based on SHA-256 file content hash, not filename
- duplicate upload returns an existing document and creates no new job
- delete uses hard delete for the initial implementation
- future work includes reprocess, soft delete/restore, and existing-data hash backfill

### Backend

Implemented:

- `documents.file_hash` model field
- partial unique index on `documents.file_hash`
- Alembic migration: `backend/alembic/versions/20260603_0002_document_file_hash.py`
- SHA-256 calculation during PDF storage
- upload deduplication in `DocumentService.create_document_from_upload`
- duplicate upload response fields:
  - `duplicate`
  - `duplicate_of_document_id`
  - nullable `job_id`
- `DELETE /api/documents/{document_id}`
- hard delete cleanup for:
  - original PDF file
  - processing jobs
  - document pages
  - document chunks
  - entity mentions
  - document-scoped knowledge edges
  - orphan entities
  - orphan knowledge nodes

### Frontend

Implemented:

- delete button for each document row
- confirm dialog before deletion
- refresh after deletion
- duplicate upload handling that does not start job progress
- duplicate upload status message

### Tests

Added:

- `backend/tests/test_document_service.py`

Covered:

- duplicate uploads are detected by file hash
- duplicate upload removes the newly saved duplicate file
- document deletion removes document-scoped DB rows and local PDF file
- orphan entity/node cleanup

## Key Decisions

- Use hard delete first. Soft delete/restore is deferred.
- Use SHA-256 file hash for deduplication.
- Deduplication is content-based, not filename-based.
- Duplicate upload returns HTTP 200 with `status="already_exists"` instead of creating a new job.
- Reprocess is deferred because it needs a clear UX and job lifecycle policy.
- Existing documents without `file_hash` are not backfilled in this implementation. New uploads get hashes.
- Document deletion during background processing is allowed. Jobs are marked with `cancel_requested` metadata before cleanup, but BackgroundTasks can still race if a worker is actively operating on the deleted document.

## Changed Files

Uncommitted lifecycle changes:

- `backend/README.md`
- `backend/alembic/versions/20260603_0002_document_file_hash.py`
- `backend/app/api/routes_documents.py`
- `backend/app/models/document.py`
- `backend/app/schemas/document.py`
- `backend/app/services/document_service.py`
- `backend/app/services/storage_service.py`
- `backend/tests/test_document_service.py`
- `docs/backend/api-design.md`
- `docs/backend/data-model.md`
- `docs/backend/ingestion-pipeline.md`
- `docs/frontend/ui-requirements.md`
- `docs/implementation-plan.md`
- `frontend/app.js`
- `frontend/styles.css`
- `docs/history/2026-06-03-document-lifecycle.md`

Unrelated/untracked file still present:

- `docs/history/2026-06-03-cancellable-ingestion.md`

## Validation Results

Ran successfully:

```powershell
backend/.venv/Scripts/python.exe -m alembic upgrade head
backend/.venv/Scripts/python.exe -m ruff check app tests
backend/.venv/Scripts/python.exe -m pytest -q --basetemp .\.pytest-tmp -p no:cacheprovider
C:\Users\hda82\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check frontend\app.js
C:\Users\hda82\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check frontend\server.js
```

Results:

- Backend tests: `21 passed, 1 warning`
- Ruff: passed
- Frontend JS syntax checks: passed
- Warning: `StarletteDeprecationWarning` from FastAPI/Starlette test client stack

Commands that initially failed or needed adjustment:

- `node --check ...` with system `node.exe` failed due to WindowsApps access denied.
- Re-ran JS syntax checks with bundled Node from Codex workspace dependencies successfully.
- First document deletion test exposed cleanup ordering issue for `knowledge_nodes -> entities`; fixed with bulk node delete before entity delete.

## Known Risks And Gaps

- Browser E2E was not performed after adding delete/duplicate UI.
- Deleting a document while a background ingestion worker is actively processing it may still race. Current implementation marks jobs cancel requested, then deletes DB rows.
- Existing documents uploaded before `file_hash` migration may have `file_hash=NULL`, so dedup only works for new uploads unless backfilled.
- There is no reprocess API yet.
- There is no soft delete/restore yet.
- Frontend uses a simple `window.confirm` dialog for deletion.
- Search/entity/graph views refresh after deletion, but selected entity state may still point to a removed entity until refresh completes.

## Recommended Next Steps

1. Run browser E2E against `http://127.0.0.1:5173`.
2. Verify:
   - upload a PDF
   - upload the same PDF again
   - confirm duplicate notice and no new job
   - delete the document from the list
   - confirm it disappears from document/entity/search/graph flows
3. Check DB counts manually after deletion if needed:
   - documents
   - document_pages
   - document_chunks
   - entity_mentions
   - entities
   - knowledge_nodes
4. Decide whether to commit lifecycle changes.
5. If committing, exclude unrelated `docs/history/2026-06-03-cancellable-ingestion.md` unless the user explicitly wants it included.
6. Consider a follow-up `POST /api/documents/{document_id}/reprocess` endpoint.
7. Consider a file hash backfill script for existing documents.

## Suggested Commit Message

```text
feat: add document lifecycle management
```

## Next Session Prompt

```text
AGENTS.md를 읽고 현재 상태를 확인해줘.
최신 push된 커밋은 afcb9e6 feat: add LLM-backed entity validation 이고,
그 이후 document lifecycle 작업이 uncommitted 상태로 남아 있어.

이번 uncommitted 작업은:
- documents.file_hash migration
- SHA-256 기반 중복 업로드 방지
- DELETE /api/documents/{document_id}
- document-scoped cleanup
- frontend 삭제 버튼과 중복 업로드 안내
- 관련 docs 업데이트

검증은 이미 통과했어:
- alembic upgrade head
- ruff check app tests
- pytest -q --basetemp .\.pytest-tmp -p no:cacheprovider => 21 passed, 1 warning
- bundled Node로 frontend/app.js, frontend/server.js --check 통과

다음으로는 브라우저에서 실제 PDF 업로드, 중복 업로드, 삭제 flow를 E2E로 확인하고,
문제가 없으면 feat: add document lifecycle management 로 커밋 준비해줘.
docs/history/2026-06-03-cancellable-ingestion.md 는 이전부터 untracked였고 이번 작업 범위가 아니니 기본적으로 제외해줘.
```
