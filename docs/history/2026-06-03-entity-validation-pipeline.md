# 2026-06-03 Entity Validation Pipeline

## Session Summary

Post-MVP quality work started after the full MVP pipeline was verified in the browser. The main issue was that entity extraction surfaced too many low-value candidates, knowledge cards were too close to raw chunks, and graph relationships were too dense and weakly explained.

This session implemented the first part of that improvement plan: entity extraction now treats rule/pattern extraction as broad candidate generation, optionally validates those candidates with an LLM, and ranks stored entities by usefulness signals.

## What Changed

- Expanded `EntityCandidate` with optional description, aliases, and validation source metadata.
- Tightened rule/pattern candidate extraction:
  - filters generic acronyms such as `PDF` and `API`
  - keeps camera/ISP domain acronyms such as `IFE`, `VFE`, `CPAS`, `CSID`
  - treats `CPAS`, `CSI`, and `DMA` as domain-relevant candidates
  - sorts candidates by confidence and entity type priority
- Added `EntityValidationService`.
  - `openai` provider uses the Responses API with JSON schema output.
  - `ollama` provider uses native `/api/chat` with structured `format` schema.
  - validation is optional and disabled by default.
  - missing model/API settings or runtime validation errors fall back to rule candidates.
- Connected validation into the ingestion worker before entity persistence.
- Added job metadata for entity candidate, accepted, rejected, and validation error counts.
- Updated existing entity merge behavior to refresh description, confidence, aliases, and validation source metadata.
- Changed entity listing order to prioritize confidence and mention count.
- Added local Ollama configuration docs using `qwen3:8b`.
- Updated Post-MVP pipeline docs for entity, knowledge card, graph, and UI improvements.

## Important Settings

Default behavior remains rule-only:

```env
ENABLE_LLM_ENTITY_VALIDATION=false
LLM_PROVIDER=openai
```

Recommended local Ollama validation settings:

```env
ENABLE_LLM_ENTITY_VALIDATION=true
LLM_PROVIDER=ollama
ENTITY_VALIDATION_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=ollama
```

Recommended model setup:

```powershell
ollama pull qwen3:8b
ollama run qwen3:8b
```

## Files Changed

- `backend/app/services/entity_extraction_service.py`
- `backend/app/services/entity_validation_service.py`
- `backend/app/services/entity_service.py`
- `backend/app/workers/ingestion_worker.py`
- `backend/app/core/config.py`
- `backend/app/prompts/entity_validation.md`
- `backend/.env.example`
- `backend/README.md`
- `backend/tests/test_entity_extraction_service.py`
- `backend/tests/test_entity_validation_service.py`
- `docs/backend/ingestion-pipeline.md`
- `docs/llm/extraction-pipeline.md`
- `docs/graph/graph-model.md`
- `docs/frontend/ui-requirements.md`
- `docs/frontend/graph-view.md`
- `docs/implementation-plan.md`

## Validation

- `backend/.venv/Scripts/python.exe -m ruff check app tests`: passed
- `backend/.venv/Scripts/python.exe -m pytest -q --basetemp .\.pytest-tmp -p no:cacheprovider`: `19 passed, 1 warning`

The warning was a pre-existing `StarletteDeprecationWarning` from the test client stack.

## Remaining Notes

- Existing uploaded PDFs need to be re-ingested to benefit from improved entity validation.
- LLM validation quality should be checked against the RK3288 ISP PDF before tuning thresholds.
- Knowledge card generation and typed graph relation extraction remain the next Post-MVP quality stages.
- `docs/history/2026-06-03-cancellable-ingestion.md` was already untracked before this work and was not included in this commit scope.
