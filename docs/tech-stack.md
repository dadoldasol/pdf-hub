# 기술 스택

## 1. 기본 스택

| 영역 | 기본 선택 | 역할 |
|---|---|---|
| Backend | Python, FastAPI | API 서버, 작업 orchestration |
| DB | PostgreSQL | 문서/청크/엔티티/관계 저장 |
| Vector DB | pgvector | 청크 임베딩 검색 |
| PDF 텍스트 추출 | PyMuPDF | 페이지 텍스트 추출, 빠른 처리 |
| 표 추출 | pdfplumber | 표 후보 추출 |
| OCR | Tesseract | 이미지 기반 PDF fallback |
| LLM | OpenAI API | 요약, 엔티티 추출, 관계 추출 |
| Frontend | React 또는 Next.js | 검색/지식 카드/그래프 UI |
| Graph View | React Flow 또는 Cytoscape.js | 엔티티 관계 시각화 |
| Migration | Alembic | DB schema versioning |
| Test | pytest | backend 테스트 |

## 2. Backend

FastAPI를 사용한다.

이유:

- Python PDF/LLM 생태계와 잘 맞는다.
- API 문서가 자동 생성된다.
- 비동기 endpoint와 background task를 쉽게 구성할 수 있다.
- 소규모 팀이 빠르게 개발하기 좋다.

권장 구조:

```text
app/
  main.py
  api/
  core/
  db/
  models/
  schemas/
  services/
  workers/
  prompts/
  tests/
```

## 3. PDF 처리

기본은 PyMuPDF로 처리한다.

- 빠른 페이지 순회
- 페이지별 텍스트 추출
- 페이지 이미지 렌더링 가능
- 원문 페이지 링크/preview 구현에 유리

pdfplumber는 표 추출에 사용한다.

- 표 후보 추출
- 셀 기반 텍스트 추출
- 표가 중요한 문서에서 보조 처리

OCR은 MVP에서 fallback으로만 둔다.

## 4. LLM 처리

MVP 기본값은 OpenAI API다.

역할:

- 문서 요약
- 페이지 요약
- 청크 요약
- 엔티티 추출
- 관계 추출
- 문서 분류

LLM 출력은 반드시 JSON schema 형태로 제한한다.

## 5. 검색

MVP 기본값:

- PostgreSQL + pgvector
- 청크 벡터 검색 우선
- 간단한 keyword filter 병행

확장:

- PostgreSQL full-text search
- BM25 기반 검색 엔진
- reranking
- entity-aware search

## 6. 그래프

MVP에서는 PostgreSQL 테이블로 node/edge를 저장한다.

기본 테이블:

- `knowledge_nodes`
- `knowledge_edges`

Neo4j는 MVP 이후에 검토한다.

## 7. Frontend

MVP에서는 빠른 구현을 우선한다.

추천:

- React SPA: 단순한 내부 도구로 빠르게 만들 때
- Next.js: 라우팅, 서버 기능, 향후 배포 구조를 고려할 때

기본 화면:

- 문서 목록
- 업로드 화면
- 검색 화면
- 지식 카드
- 엔티티 상세
- 그래프 뷰
- PDF 원문 페이지 링크

