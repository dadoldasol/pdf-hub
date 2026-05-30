# 상세 구현 계획

## 1. Backend

### 만들 것

- FastAPI 기반 API 서버
- PDF 업로드 API
- 문서/페이지/청크/엔티티 조회 API
- 검색 API
- 그래프 API
- 처리 작업 상태 API

### 프로젝트 구조

```text
app/
  main.py
  api/
    routes_documents.py
    routes_search.py
    routes_entities.py
    routes_graph.py
    routes_jobs.py
  core/
    config.py
    logging.py
  db/
    session.py
    base.py
  models/
    document.py
    chunk.py
    entity.py
    graph.py
    job.py
  schemas/
    document.py
    search.py
    entity.py
    graph.py
  services/
    document_service.py
    storage_service.py
    search_service.py
    graph_service.py
  workers/
    ingestion_worker.py
  prompts/
    entity_extraction.md
    summary.md
```

### 주요 API

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/documents/upload` | PDF 업로드 및 처리 job 생성 |
| GET | `/api/documents` | 문서 목록 |
| GET | `/api/documents/{document_id}` | 문서 상세 |
| GET | `/api/documents/{document_id}/pages/{page_number}` | 페이지 원문 텍스트 |
| GET | `/api/jobs/{job_id}` | 처리 상태 |
| POST | `/api/search` | 검색 |
| GET | `/api/entities` | 엔티티 목록 |
| GET | `/api/entities/{entity_id}` | 엔티티 상세 |
| GET | `/api/entities/{entity_id}/knowledge-card` | 지식 카드 |
| GET | `/api/graph/entities/{entity_id}` | 관련 그래프 |

### 비동기 작업 처리

MVP:

- FastAPI upload endpoint는 파일 저장과 job 생성까지만 수행한다.
- worker 함수가 PDF 처리, LLM 처리, embedding 생성을 순차 실행한다.
- 작업 상태는 `processing_jobs`에 저장한다.

상태값:

```text
queued
extracting_pdf
chunking
embedding
extracting_knowledge
completed
failed
```

## 2. PDF Processing

### 만들 것

- 페이지별 텍스트 추출
- 청크 생성
- 표 후보 추출
- 이미지 기반 PDF 감지
- OCR fallback hook
- 원문 위치 추적

### PyMuPDF와 pdfplumber 역할

| 도구 | 역할 |
|---|---|
| PyMuPDF | 기본 텍스트 추출, 페이지 수 확인, 페이지 렌더링 |
| pdfplumber | 표 추출, layout이 중요한 문서 보조 분석 |

### 처리 단계

```text
1. PDF 열기
2. 페이지 수 확인
3. 페이지별 text 추출
4. text 길이가 너무 짧으면 image-based page 후보로 표시
5. pdfplumber로 table 후보 추출
6. page record 저장
7. chunk 생성
8. chunk에 document_id/page_number/source_text 저장
```

### OCR fallback

MVP:

- OCR은 자동 고도화하지 않는다.
- 텍스트가 거의 없는 페이지를 `needs_ocr=true`로 표시한다.
- Tesseract fallback을 옵션으로 둔다.

추후:

- PaddleOCR로 표/도식 OCR 품질 개선
- 페이지 이미지 cache 저장

### 원문 위치 추적

MVP 필수:

- `document_id`
- `page_number`
- `chunk_index`

후순위:

- bbox
- text span offset
- 페이지 이미지 highlight

## 3. LLM Pipeline

### 만들 것

- 문서 요약
- 페이지 요약
- 청크 요약
- 엔티티 추출
- 관계 추출
- 문서 분류
- prompt version 관리
- 결과 검증

### 엔티티 타입

```text
ISP_BLOCK
CAMERA_HAL
KERNEL_DRIVER
CHIPSET
CODE_FILE
FUNCTION
DEBUG_KEYWORD
FEATURE
LIMITATION
CALL_FLOW
REGISTER
CLOCK
BANDWIDTH
```

### 관계 타입

```text
IMPLEMENTS
SUPPORTS
LIMITED_BY
DEBUGGED_BY
CALLS
DEPENDS_ON
CHANGED_IN
RELATED_TO
MENTIONED_IN
```

### LLM 출력 원칙

- JSON으로만 출력하도록 prompt를 작성한다.
- schema validation을 통과한 결과만 구조화 테이블에 저장한다.
- 실패한 raw output은 별도 컬럼에 저장한다.
- source chunk id를 항상 포함한다.

### 결과 검증

체크 항목:

- entity name이 비어 있지 않은가
- source chunk id가 존재하는가
- relation source/target entity가 존재하는가
- confidence가 낮은 relation은 UI에서 약하게 표시하는가

## 4. Search

### 만들 것

- 벡터 검색
- 키워드 검색
- 하이브리드 검색 hook
- 검색 결과 원문 페이지 링크

### 벡터 검색

입력 query를 embedding으로 변환한 뒤 `document_chunks.embedding`과 cosine similarity로 검색한다.

반환 필드:

- chunk id
- document id
- document title
- page number
- snippet
- score
- related entities

### 키워드 검색

MVP에서는 단순 `ILIKE` 또는 PostgreSQL full-text search를 사용한다.

중요 키워드:

- 코드 파일명
- 함수명
- log keyword
- chipset name
- ISP block name

### 하이브리드 검색

MVP 이후 vector score와 keyword score를 합산한다.

```text
final_score = vector_score * 0.7 + keyword_score * 0.3
```

가중치는 검색 로그를 보고 조정한다.

## 5. Graph

### 만들 것

- PostgreSQL 기반 node/edge 테이블
- 엔티티 간 관계 저장
- 엔티티 중심 1-hop 탐색 API
- 그래프 UI용 JSON 응답

### 테이블 설계

```text
knowledge_nodes
- id
- node_type
- name
- normalized_name
- description
- metadata jsonb
- created_at
- updated_at

knowledge_edges
- id
- source_node_id
- target_node_id
- edge_type
- confidence
- source_chunk_id
- metadata jsonb
- created_at
```

### 그래프 탐색 API

```text
GET /api/graph/entities/{entity_id}?depth=1&edge_type=SUPPORTS
```

응답:

```json
{
  "nodes": [],
  "edges": []
}
```

### Neo4j 도입 기준

- 2-hop 이상 탐색이 빈번하다.
- relation path query가 주요 기능이 된다.
- 그래프 알고리즘이 필요하다.
- PostgreSQL recursive query가 복잡해진다.

## 6. Frontend

### 만들 것

- PDF 업로드 화면
- 문서 목록 화면
- 검색 화면
- 지식 카드 화면
- 엔티티 상세 화면
- 그래프 뷰
- PDF 원문 페이지 링크

### 화면별 요구사항

| 화면 | 필수 기능 |
|---|---|
| 문서 목록 | 파일명, 처리 상태, 페이지 수, 업로드 시간 |
| 업로드 | PDF 선택, 업로드 진행, job 상태 표시 |
| 검색 | query 입력, top-k 결과, page link |
| 지식 카드 | 요약, 기능, 구현 위치, 디버깅 키워드, 한계 |
| 엔티티 상세 | 관련 청크, 관련 문서, 관계 목록 |
| 그래프 뷰 | 노드/엣지 표시, 노드 클릭, depth 조절 |

## 7. Operations

### 로컬 개발

필수 구성:

- Python 3.11+
- PostgreSQL 15+
- pgvector extension
- Node.js 20+
- `.env`

### 환경 변수

```text
DATABASE_URL=
OPENAI_API_KEY=
EMBEDDING_MODEL=
LLM_MODEL=
PDF_STORAGE_DIR=
```

### Migration

- Alembic 사용
- schema 변경은 migration으로만 반영
- 초기 seed script로 샘플 문서 metadata를 생성할 수 있게 한다.

### 테스트 전략

| 테스트 | 대상 |
|---|---|
| unit test | chunker, parser, schema validator |
| integration test | upload, search, graph API |
| fixture test | 샘플 PDF 처리 |
| regression test | LLM output schema validation |

### 로그/모니터링

MVP:

- job status
- error message
- LLM parse failure count
- PDF processing duration

후순위:

- OpenTelemetry
- Prometheus/Grafana
- alerting

