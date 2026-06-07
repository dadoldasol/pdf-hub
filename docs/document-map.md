# 문서 맵

이 문서는 `docs/` 아래에 둘 문서들의 목적, 주요 내용, 읽는 대상, 구현 활용 방식을 정의한다.

## 1. 최상위 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `README.md` | 문서 전체 진입점 | 문서 목록, 읽는 순서, 완료된 MVP와 고도화 목표 | 전체 팀, LLM/Codex | 어떤 문서를 먼저 볼지 판단 |
| `project-overview.md` | 제품 목표와 문제 정의 | 사용자, 시나리오, 범위, 성공 기준 | 기획자, 개발자 | 기능 우선순위 결정 |
| `architecture.md` | 시스템 구조 정의 | 컴포넌트, 데이터 흐름, 저장소, 작업 처리 | 백엔드/AI 개발자 | 모듈 경계와 API 설계 기준 |
| `tech-stack.md` | 기술 스택 정리 | 영역별 기본 기술과 역할 | 전체 개발자 | 라이브러리 선택과 초기 세팅 |
| `mvp-scope.md` | 완료된 MVP 기준 | 포함/제외 기능, API, 데이터 모델 | 전체 팀 | 회귀 방지 기준 |
| `roadmap.md` | 단계별 일정 | 6주 개발 계획, 산출물, 완료 기준 | 전체 팀 | 주차별 구현 계획 |
| `implementation-plan.md` | 상세 구현 항목 | backend/pdf/llm/search/graph/frontend/operations | 개발자, LLM/Codex | 구현 task 생성 |
| `technology-decisions.md` | 주요 기술 선택 기준 | DB, LLM, OCR, frontend 선택 기준 | 기술 리더, 개발자 | 기술 변경 판단 |

## 2. Backend 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `backend/api-design.md` | API 계약 정의 | endpoint, request/response, error format | 백엔드/프론트엔드 | API 구현과 UI 연동 |
| `backend/data-model.md` | DB schema 정의 | tables, columns, indexes, relations | 백엔드 | migration 작성 |
| `backend/ingestion-pipeline.md` | 업로드와 refinement 처리 흐름 정의 | job type, 파일 저장, ingestion/refinement 단계 | 백엔드/AI | worker 구현 |

## 3. PDF 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `pdf/pdf-processing.md` | PDF 텍스트/표 추출 기준 | PyMuPDF, pdfplumber, chunking | AI/백엔드 | 추출 파이프라인 구현 |
| `pdf/ocr-strategy.md` | OCR fallback 기준 | 이미지 PDF 감지, Tesseract/PaddleOCR | AI/백엔드 | OCR 도입 판단 |

## 4. LLM 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `llm/extraction-pipeline.md` | LLM refinement 흐름 정의 | entity description, knowledge card, relation 방향 | AI 개발자 | refinement 구현 |
| `llm/prompt-design.md` | 프롬프트 관리 기준 | JSON schema, prompt versioning | AI 개발자 | prompt template 작성 |
| `llm/evaluation.md` | 품질 평가 기준 | 샘플셋, precision, source validation | AI 개발자 | 회귀 테스트 |

## 5. Search 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `search/vector-search.md` | 벡터 검색 구현 기준 | embedding, pgvector, top-k | 백엔드/AI | search API 구현 |
| `search/keyword-search.md` | 키워드 검색 구현 기준 | exact match, full-text search | 백엔드 | 코드 파일명/log keyword 검색 |
| `search/hybrid-search.md` | 하이브리드 검색 설계 | vector + keyword merge, ranking | 백엔드/AI | 검색 품질 개선 |

## 6. Graph 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `graph/graph-model.md` | 그래프 모델 정의 | node/edge type, relation taxonomy | 백엔드/AI | 관계 저장 |
| `graph/graph-query.md` | 그래프 탐색 API 정의 | neighbor query, depth, filtering | 백엔드/프론트엔드 | graph API와 UI 구현 |

## 7. Frontend 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `frontend/ui-requirements.md` | 화면 요구사항 정의 | 문서 목록, 검색, 카드, 상세 | 프론트엔드 | UI task 생성 |
| `frontend/graph-view.md` | 그래프 뷰 요구사항 | layout, interaction, filtering | 프론트엔드 | 그래프 화면 구현 |

## 8. Operations 문서

| 문서 | 목적 | 주요 내용 | 대상 | 구현 활용 |
|---|---|---|---|---|
| `operations/local-dev.md` | 로컬 개발 환경 정의 | dev script, env, docker compose, worker 실행 | 개발자 | 온보딩 |
| `operations/deployment.md` | 배포 방식 정의 | backend/frontend/db 배포 | 개발자 | 운영 환경 구성 |
| `operations/monitoring.md` | 로그/모니터링 기준 | job logs, error logs, metrics | 개발자 | 장애 확인 |
