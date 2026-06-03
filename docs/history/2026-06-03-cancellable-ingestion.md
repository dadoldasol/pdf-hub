# 2026-06-03 Cancellable Ingestion

## 세션 요약

대형 또는 복잡한 PDF 업로드 후 컴퓨터가 멈추거나 작업 진행 상태를 알기 어려운 문제를 줄이기 위해 PDF ingestion 흐름을 배치 처리 중심으로 개선했다.
프론트엔드에는 업로드 후 단계별 job 진행률과 작업 중지 버튼을 추가했고, 백엔드에는 cancel API와 협력적 cancel 처리 로직을 추가했다.
변경사항은 `a29ac9f feat: add cancellable PDF ingestion progress`로 커밋했고 `origin/main`에 push 완료했다.

## 프로젝트 현재 상태

- Backend MVP와 Frontend MVP는 구현되어 있다.
- PDF 업로드, 페이지 텍스트 추출, 청크 생성, deterministic local embedding, rule/pattern entity extraction, 검색, 지식 카드, co-mention graph 흐름이 동작한다.
- 최신 커밋은 `a29ac9f feat: add cancellable PDF ingestion progress`다.
- 작업 트리는 커밋/푸시 직후 clean이었다. 단, `backend/.pytest_cache/` 권한 문제로 `git status`에서 warning이 계속 보인다.

## 완료한 작업

- PDF processing service에 페이지 단위 iterator를 추가했다.
- 기본 텍스트 추출 모드를 `blocks` 기반으로 바꾸고, `PDF_TEXT_EXTRACTION_MODE` 설정을 추가했다.
- ingestion worker를 전체 PDF 결과를 한 번에 들고 처리하는 구조에서 페이지/청크 배치 처리 구조로 변경했다.
- job metadata에 `total_pages`, `processed_pages`, `total_chunks`, `processed_chunks`, `entity_mentions`, 현재 페이지, 페이지별 처리 시간 등을 기록하도록 했다.
- `POST /api/jobs/{job_id}/cancel` API를 추가했다.
- worker가 page/chunk/embedding/entity batch 경계에서 `cancel_requested`를 확인하고 `canceled` 상태로 안전하게 멈추도록 했다.
- 실패 시 빈 `error_message`가 남지 않도록 예외 타입을 함께 저장하도록 보강했다.
- 프론트엔드 업로드 영역에 단계별 진행률, 현재 페이지, 최근 페이지 처리 시간, 작업 중지 버튼을 추가했다.
- `frontend/README.md`, `backend/README.md`, `docs/operations/local-dev.md`에 backend/frontend 재실행 방법과 최신 API 흐름을 반영했다.
- 사용자가 업로드한 `rk3288-chapter-31-image-signal-processing-(isp).pdf`는 직접 재실행 시 정상 처리됨을 확인했다.

## 주요 결정 사항

- MVP 단계에서는 별도 Celery/Redis 큐를 도입하지 않고 FastAPI `BackgroundTasks` 기반 worker를 유지한다.
- 작업 중지는 즉시 강제 종료가 아니라 DB metadata 기반 협력적 cancel로 처리한다.
- PyMuPDF가 특정 페이지의 `get_text` 내부에서 오래 걸리는 동안은 즉시 중단할 수 없다. 해당 호출이 끝난 뒤 cancel을 감지한다.
- 기본 PDF 텍스트 추출은 `blocks` 모드로 시작하고, 필요 시 `.env`에서 `PDF_TEXT_EXTRACTION_MODE=text`로 되돌릴 수 있다.
- frontend는 이제 일반 `node frontend\server.js` 명령 기준으로 문서화한다.

## 변경/생성한 주요 파일

- `backend/app/services/pdf_processing_service.py`: 페이지 단위 추출, `blocks` 모드, 페이지별 소요 시간 추가
- `backend/app/workers/ingestion_worker.py`: 배치 처리, 진행률 metadata, cancel 처리, 실패 메시지 보강
- `backend/app/api/routes_jobs.py`: `POST /api/jobs/{job_id}/cancel` 추가
- `backend/app/schemas/job.py`: `extra_metadata` 응답 포함
- `backend/app/core/config.py`: ingestion batch, embedding toggle, text extraction mode 설정 추가
- `frontend/app.js`: job polling, 진행률 표시, 작업 중지 요청 처리 추가
- `frontend/index.html`: 진행률 UI와 작업 중지 버튼 추가
- `frontend/styles.css`: 진행률/작업 중지 UI 스타일 추가
- `backend/README.md`: backend/frontend 실행과 cancel API 문서화
- `frontend/README.md`: `node frontend\server.js` 실행으로 업데이트
- `docs/operations/local-dev.md`: 로컬 frontend 실행 방식 업데이트

## 검증 결과

- `backend/.venv/Scripts/python.exe -m ruff check app tests`: 통과
- `backend/.venv/Scripts/python.exe -m pytest -q --basetemp .\.pytest-tmp -p no:cacheprovider`: `12 passed, 1 warning`
- bundled Node로 `frontend/app.js` 문법 검사: 통과
- bundled Node로 `frontend/server.js` 문법 검사: 통과
- 커밋 생성: `a29ac9f feat: add cancellable PDF ingestion progress`
- push 완료: `origin main`

## 실행하지 못한 검증

- 프론트 브라우저에서 작업 중지 버튼을 실제 클릭해 cancel이 UI에 반영되는 end-to-end 시각 검증은 별도로 기록하지 못했다.
- 큰 PDF 여러 개를 연속 업로드하는 장시간 부하 검증은 아직 하지 않았다.

## 미검증/리스크

- PyMuPDF의 한 페이지 추출 호출이 매우 오래 걸리면 협력적 cancel은 그 호출이 끝날 때까지 반영되지 않는다.
- 완전한 즉시 중지는 별도 프로세스 worker와 timeout/kill 구조가 필요하다.
- deterministic local embedding과 rule-based entity extraction은 실제 도메인 PDF 품질 검증 후 개선이 필요하다.
- `backend/.pytest_cache/` 권한 문제로 `git status` warning이 계속 보인다.
- 실제 frontend 실행은 사용자 환경의 `node` 명령을 기준으로 문서화했다. Codex 셸에서는 WindowsApps `node.exe` 접근 제한이 있었고 bundled Node로 문법 검사를 수행했다.

## 남은 작업

- 실제 브라우저에서 PDF 업로드 후 작업 중지 버튼 클릭 흐름 검증
- 16페이지 RK3288 ISP PDF와 더 큰 PDF 1~3개로 업로드, 진행률, cancel, 검색, 엔티티, 지식 카드 흐름 검증
- 필요 시 `INGESTION_BATCH_PAGES`, `INGESTION_BATCH_CHUNKS`, `ENABLE_EMBEDDINGS_ON_UPLOAD` 값을 실제 부하 기준으로 조정
- 특정 페이지 추출이 오래 걸리는 PDF가 반복되면 별도 프로세스 기반 text extraction timeout 설계 검토
- `backend/.pytest_cache/` 권한 warning 정리 방법 검토

## 다음 작업 순서

1. `git status --short`로 작업 트리 확인
2. backend/frontend 서버 재실행
3. `http://127.0.0.1:5173`에서 PDF 업로드
4. 진행률에 현재 페이지와 최근 페이지 처리 시간이 보이는지 확인
5. 작업 중지 버튼을 눌러 job/document status가 `canceled`로 바뀌는지 확인
6. 동일 PDF를 다시 업로드해 정상 완료되는지 확인
7. 검색, 엔티티, 지식 카드, 그래프 뷰까지 확인
8. 결과에 따라 worker 분리 또는 timeout 설계 여부 결정

## 다음 세션 프롬프트

```text
AGENTS.md를 읽고 현재 상태를 확인해줘.
최신 커밋은 a29ac9f feat: add cancellable PDF ingestion progress 이고 origin/main에 push 완료됐어.
이번 세션에서는 PDF ingestion 배치 처리, job 진행률 UI, 작업 중지 API/버튼, README 실행 명령 업데이트를 완료했어.
다음 작업은 실제 브라우저에서 PDF 업로드 후 진행률과 작업 중지 버튼을 end-to-end로 검증하는 거야.
backend는 C:\dasol_works\pdf_hub\backend 에서 .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload 로 실행하고,
frontend는 C:\dasol_works\pdf_hub 에서 node frontend\server.js 로 실행하면 돼.
먼저 git status, 서버 상태, DB 상태를 확인한 뒤 PDF 업로드, cancel, 재업로드, 검색/엔티티/지식 카드 흐름을 검증해줘.
```
