# 2026-06-06 Resilient Ingestion Handoff

## 세션 요약

MVP 검증 이후 큰 PDF 업로드 시 PDF 텍스트 추출 단계에서 서버 또는 PC가 멈추는 문제를 줄이기 위해 ingestion 구조를 고도화했다.

핵심 변화는 FastAPI API 서버와 PDF 처리 worker를 분리하고, 페이지별 텍스트 추출을 child process timeout 경계 안에서 실행하도록 만든 것이다. 이제 업로드 API는 PDF 저장과 `queued` job 생성까지만 수행하고, 별도 ingestion worker가 job을 claim해서 처리한다. 특정 페이지가 timeout/failed 되어도 실패 페이지 row를 남기고 나머지 페이지 처리를 계속할 수 있다.

세션 후반에는 삭제한 문서의 orphan entity가 UI에 남는 문제도 수정했다. 현재 로컬 DB에서 삭제 후 남아 있던 orphan `IFE`, `CSID` entity/node는 정리했고, `/api/entities`는 빈 목록을 반환한다.

## 프로젝트 현재 상태

- Branch: `main`
- Remote: `origin/main`
- 최신 커밋: `2c6d569 fix: remove orphan entities after document deletion`
- 추적 파일 기준 working tree는 history 파일 생성 전 clean이었다.
- Backend/Frontend MVP는 구현 완료 상태다.
- 큰 PDF 안정성 관련 ingestion 고도화가 반영되었다.
- 업로드 후 실제 처리를 진행하려면 backend 서버와 별도로 ingestion worker를 실행해야 한다.

실행 기준:

```powershell
cd C:\dasol_works\pdf_hub\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
.\.venv\Scripts\python.exe -m app.workers.worker_main
```

프론트:

```powershell
cd C:\dasol_works\pdf_hub
node frontend\server.js
```

## 완료한 작업

- Upload API와 ingestion worker 분리
- DB polling 기반 worker entrypoint 추가: `python -m app.workers.worker_main`
- 페이지 단위 저장/commit 강화
- PyMuPDF 페이지 추출을 child process timeout 경계로 격리
- timeout/failed 페이지도 `document_pages` row로 저장
- `extraction_status`, `extraction_error`, `extraction_seconds` 필드 추가
- 일부 페이지 실패 시 `partially_processed` 상태 지원
- 기존 성공 페이지를 먼저 삭제하지 않고 resume 처리
- cancel 요청 시 진행 중인 page extraction child process terminate
- `blocks` mode 실패 시 `text` mode fallback retry
- Frontend job progress에서 부분 완료/실패 페이지 수 표시
- ingestion 중 LLM entity validation을 별도 스위치로 분리
- 문서 삭제 후 orphan entity/node cleanup 보강
- mention 없는 orphan entity가 `/api/entities`와 entity detail에 노출되지 않도록 필터링
- 관련 테스트와 문서 업데이트

## 주요 결정 사항

- 큰 PDF 안정성을 위해 FastAPI `BackgroundTasks` 기반 처리에서 별도 worker 프로세스 방식으로 전환했다.
- Queue 인프라는 아직 Redis/Celery 없이 PostgreSQL polling/claim 방식으로 유지한다.
- 페이지 하나가 멈춰도 전체 PDF와 API 서버가 멈추지 않도록 child process timeout을 사용한다.
- timeout/failed 페이지는 삭제하지 않고 DB에 실패 row로 남긴다.
- 일부 페이지만 실패한 문서는 `partially_processed` 상태로 두고, 처리된 페이지/청크/검색 데이터는 사용 가능하게 한다.
- upload ingestion 중 LLM 호출은 기본 비활성화한다.
- LLM 기반 entity validation/knowledge card description 생성은 향후 별도 refinement job으로 분리하는 것이 권장된다.

## LLM 지식카드 관련 메모

오늘 수정 후 지식카드에서 “ISP가 무엇인지” 같은 개념 설명이 줄어든 것은 의도된 안정화 결과다.

이전에는 ingestion 중 Ollama LLM validation이 entity description을 채울 수 있었지만, 이 호출이 큰 PDF 처리 중 서버 지연/멈춤의 원인이 될 수 있어 다음처럼 분리했다.

```env
ENABLE_LLM_ENTITY_VALIDATION=true
ENABLE_LLM_ENTITY_VALIDATION_ON_INGESTION=false
```

의미:

- `ENABLE_LLM_ENTITY_VALIDATION`: LLM entity validation 기능 자체의 일반 스위치
- `ENABLE_LLM_ENTITY_VALIDATION_ON_INGESTION`: PDF 업로드 ingestion 중 LLM 호출 허용 여부

추후 추천 방향:

```text
upload ingestion 안정 처리
  -> rule/pattern entity 저장
  -> 사용자가 요청하거나 별도 worker가 refinement job 실행
  -> LLM entity validation
  -> entity description 생성
  -> knowledge card summary 생성
```

## 변경/생성한 주요 파일

Backend:

- `backend/app/api/routes_documents.py`: upload에서 BackgroundTasks 제거
- `backend/app/workers/worker_main.py`: DB polling worker 추가
- `backend/app/workers/ingestion_worker.py`: 페이지 단위 commit, resume, partial status, cancel, LLM 분리 반영
- `backend/app/services/pdf_processing_service.py`: page timeout isolation, cancel, fallback retry
- `backend/app/services/document_service.py`: orphan entity/node cleanup 보강
- `backend/app/services/entity_service.py`: mention 없는 orphan entity 조회 제외
- `backend/app/services/entity_validation_service.py`: enabled override 추가
- `backend/app/models/document.py`: page extraction status 필드 추가
- `backend/app/schemas/document.py`: page extraction status 응답 추가
- `backend/app/core/config.py`: worker, timeout, fallback, ingestion LLM settings 추가
- `backend/alembic/versions/20260606_0003_page_extraction_status.py`: page extraction status migration
- `backend/.env.example`: `ENABLE_LLM_ENTITY_VALIDATION_ON_INGESTION` 추가

Frontend:

- `frontend/app.js`: `partially_processed`, 실패/timeout 페이지 progress 표시

Tests:

- `backend/tests/test_documents_api.py`
- `backend/tests/test_entity_service.py`
- `backend/tests/test_ingestion_worker.py`
- `backend/tests/test_pdf_processing_service.py`
- `backend/tests/test_document_service.py`
- `backend/tests/test_entity_validation_service.py`

Docs:

- `backend/README.md`
- `docs/architecture.md`
- `docs/backend/data-model.md`
- `docs/backend/ingestion-pipeline.md`
- `docs/implementation-plan.md`
- `docs/operations/local-dev.md`

## 생성된 주요 커밋

```text
f86a3fc feat: split ingestion worker from upload API
b9d2349 fix: commit ingestion pages incrementally
ea94176 feat: isolate PDF page extraction with timeout
107d8d8 feat: record PDF page extraction failures
e5b2056 feat: mark ingestion as partially processed
475cce5 feat: resume ingestion without clearing completed pages
bd97a12 feat: cancel in-flight page extraction
0fc6a1f feat: retry PDF text extraction with fallback mode
f982537 feat: show partial ingestion progress in frontend
63270fa feat: decouple LLM validation from ingestion
f789baa test: cover queued upload workflow
ca21d3c docs: document resilient ingestion workflow
2c6d569 fix: remove orphan entities after document deletion
```

## 검증 결과

세션 중 반복적으로 실행해 통과:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q --basetemp .\.pytest-tmp -p no:cacheprovider
node --check frontend\app.js
node --check frontend\server.js
curl.exe -I http://127.0.0.1:5173
```

최종 주요 결과:

- Backend tests: `35 passed, 1 warning`
- Ruff: passed
- Alembic: head 적용 확인
- Frontend JS syntax: passed
- Frontend server: HTTP 200 확인
- `/api/entities`: 문서 삭제 후 빈 목록 확인

경고:

- `StarletteDeprecationWarning` from FastAPI/Starlette test client stack
- `git status`에서 `backend/.pytest_cache/` 권한 경고가 반복될 수 있음

## 실행하지 못한 검증

- 실제 브라우저에서 큰 PDF를 장시간 업로드하며 cancel/timeout/partial UI를 시각적으로 끝까지 검증하지는 못했다.
- 여러 개의 큰 PDF를 연속 업로드하는 부하 검증은 아직 수행하지 않았다.
- LLM refinement job은 아직 구현하지 않았으므로 지식카드 description 품질 회복은 다음 작업이다.

## 미검증/리스크

- worker를 실행하지 않으면 업로드 job은 `queued` 상태에서 대기한다.
- 현재 backend uvicorn 프로세스가 중복 실행될 수 있으므로 개발 중에는 backend 1개, worker 1개, frontend 1개로 정리하는 것이 좋다.
- child process timeout은 특정 페이지가 전체 시스템을 멈추는 것을 줄이지만, 매우 큰 PDF 다중 처리에는 worker concurrency/resource policy가 더 필요할 수 있다.
- `partially_processed` 문서에서 검색/엔티티는 처리된 페이지 기준으로 동작하지만, 실패 페이지 재처리 API는 아직 없다.
- LLM validation을 ingestion 중 다시 켜면 Ollama 지연 문제가 재발할 수 있다.

## 남은 작업

1. 실제 큰 PDF로 end-to-end 검증
2. backend/frontend/worker 실행 프로세스 정리 또는 개발용 통합 실행 스크립트 추가
3. 실패/timeout 페이지 재처리 API 설계
4. LLM refinement job 추가
5. knowledge card summary/description 생성 파이프라인 구현
6. frontend에서 worker 미실행 상태를 더 명확히 안내
7. 장시간/다중 PDF 부하 검증

## 다음 작업 순서

1. 서버 중복 프로세스를 정리한다.
2. backend, frontend, ingestion worker를 각각 1개씩 실행한다.
3. RK3288 ISP PDF 또는 더 큰 PDF를 업로드한다.
4. job이 `queued -> claimed -> extracting_pdf -> chunking -> embedding -> extracting_knowledge -> completed/partially_processed`로 이동하는지 확인한다.
5. timeout/failed page가 생기면 DB의 `document_pages.extraction_status`를 확인한다.
6. 문서 삭제 후 `/api/entities`가 orphan entity를 노출하지 않는지 확인한다.
7. 다음 기능으로 LLM refinement job을 설계한다.

## 다음 세션 프롬프트

```text
AGENTS.md를 읽고 현재 상태를 확인해줘.
최신 커밋은 2c6d569 fix: remove orphan entities after document deletion 이고 origin/main에 push 완료됐어.

오늘 세션에서 큰 PDF 안정성을 위해:
- upload API와 ingestion worker를 분리했고
- page 단위 commit을 적용했고
- PyMuPDF page extraction을 child process timeout/cancel 경계로 격리했고
- failed/timeout page row와 partially_processed 상태를 추가했고
- 기존 완료 페이지를 삭제하지 않고 resume 처리하도록 바꿨고
- blocks 실패 시 text fallback retry를 추가했고
- frontend progress에 부분 완료/실패 페이지 표시를 추가했고
- ingestion 중 LLM validation을 ENABLE_LLM_ENTITY_VALIDATION_ON_INGESTION=false 기본값으로 분리했고
- 문서 삭제 후 orphan entity/node cleanup과 entity 목록 필터를 고쳤어.

주의:
- 업로드 후 실제 처리는 별도 worker가 필요해.
  backend: C:\dasol_works\pdf_hub\backend 에서 .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
  worker:  C:\dasol_works\pdf_hub\backend 에서 .\.venv\Scripts\python.exe -m app.workers.worker_main
  frontend: C:\dasol_works\pdf_hub 에서 node frontend\server.js
- worker가 없으면 job은 queued 상태로 계속 대기한다.
- LLM description/knowledge card 품질은 ingestion 중 LLM을 꺼서 단순해졌다.

다음으로는 실제 큰 PDF end-to-end 검증을 하고,
그 다음 LLM refinement job을 설계해줘.
목표는 upload ingestion 안정성은 유지하면서, 별도 작업으로 entity description과 knowledge card summary를 다시 생성하는 거야.
```
