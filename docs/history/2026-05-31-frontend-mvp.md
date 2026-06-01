# 2026-05-31 Frontend MVP

## 세션 요약

Backend MVP와 Frontend MVP를 기본 동작 가능한 상태로 구현하고 각각 커밋했다.
현재 워킹트리는 세션 기록/스킬 변경 전 기준으로 clean이었고, 프론트는 `http://127.0.0.1:5173/`에서 백엔드 API 연결까지 확인했다.

## 프로젝트 현재 상태

- Backend MVP 구현 완료
- Frontend MVP 구현 완료
- PostgreSQL + pgvector 기반 데이터 저장/검색 흐름 구현
- 정적 프론트 UI에서 PDF 업로드, 문서 목록, 검색, 엔티티, 지식 카드, 그래프 뷰 연결
- 현재 브라우저 URL: `http://127.0.0.1:5173/`
- 백엔드 API 문서: `http://127.0.0.1:8000/docs`

## 완료한 작업

- Backend MVP 마무리 및 커밋
- Frontend MVP 구현 및 커밋
- `127.0.0.1:5173` 프론트 호출을 위한 백엔드 CORS 기본값 보강
- `end-session`, `handoff` 결과를 `docs/history/`에 저장하도록 로컬 스킬 규칙 업데이트

## 주요 결정 사항

- MVP는 OpenAI/LLM 없이 deterministic local embedding + rule/pattern entity extraction으로 진행한다.
- 검색 품질과 엔티티 품질은 실제 PDF 검증 후 OpenAI embedding/LLM extraction으로 개선한다.
- 그래프는 Neo4j 없이 PostgreSQL 기반 데이터와 co-mention 관계로 시작한다.
- 프론트는 Next.js가 아니라 dependency-free static MVP로 시작한다.
- 앞으로 `end-session`/`handoff` 결과는 `docs/history/YYYY-MM-DD-작업내용.md`에 저장하고, 다음 세션 프롬프트까지 같은 파일에 포함한다.

## 변경/생성한 주요 파일

- `backend/app/core/config.py`
- `frontend/README.md`
- `frontend/server.js`
- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`
- `.codex/skills/end-session/SKILL.md`
- `.codex/skills/handoff/SKILL.md`
- `docs/history/2026-05-31-frontend-mvp.md`

## 커밋

- `990c6d3 feat: complete backend MVP knowledge flow`
- `57a82c1 feat: add frontend MVP`

## 검증 결과

- `node --check frontend/server.js`: 통과
- `node --check frontend/app.js`: 통과
- `backend/.venv/Scripts/pytest.exe`: 12 passed, 1 warning
- `backend/.venv/Scripts/ruff.exe check app tests`: 통과
- `GET http://127.0.0.1:8000/health`: OK
- `GET http://127.0.0.1:5173`: 200 OK
- 인앱 브라우저에서 `API 연결됨` 확인

## 실행하지 못한 검증

- 실제 Android Camera/ISP 도메인 PDF로 end-to-end 업로드, 검색, 엔티티, 지식 카드 품질 검증은 아직 하지 않았다.

## 미검증/리스크

- 실제 PDF 데이터셋 기준 검색 품질은 아직 모른다.
- rule 기반 엔티티 추출은 사전에 없는 도메인 개념을 놓칠 수 있다.
- 현재 DB에 `graph-test failed` 같은 테스트성 문서가 남아 있다.
- OCR, 표 추출, LLM 요약/관계 추출은 후순위다.

## 남은 작업

- 실제 PDF 1~3개로 업로드부터 검색/엔티티/지식 카드까지 end-to-end 검증
- 실패 문서/테스트 문서 정리 방법 추가 또는 관리 API 검토
- 검색 결과 품질을 보고 embedding provider를 OpenAI로 교체할지 판단
- 엔티티 추출 결과를 보고 rule 사전 확장 또는 LLM 추출 파이프라인 설계
- 프론트에서 업로드 진행 상태와 실패 메시지 표시 개선

## 다음 작업 순서

1. `git status --short`로 워킹트리 확인
2. Docker/PostgreSQL 상태 확인
3. 백엔드와 프론트 서버 상태 확인
4. 실제 PDF 업로드 실행
5. job 완료/실패 상태 확인
6. 검색 결과, 엔티티 목록, 지식 카드, 그래프 뷰 확인
7. 검증 결과를 바탕으로 다음 개선 범위 결정

## 다음 세션 프롬프트

```text
AGENTS.md를 읽고 현재 상태를 확인해줘.
최근 커밋은 57a82c1 feat: add frontend MVP야.
Backend/Frontend MVP는 구현 및 커밋 완료됐고, 다음 작업은 실제 PDF로 end-to-end 검증하는 거야.
브라우저는 http://127.0.0.1:5173, 백엔드는 http://127.0.0.1:8000 기준으로 확인하면 돼.
먼저 git status, 서버 상태, DB 상태를 확인한 뒤 실제 PDF 업로드/검색/엔티티/지식 카드 흐름을 검증해줘.
```
