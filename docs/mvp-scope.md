# MVP 범위

## 1. MVP 목표

MVP의 목표는 PDF를 업로드하고, 텍스트를 추출하고, 검색 가능한 지식 카드로 보여주는 것이다.

MVP에서 반드시 답해야 하는 질문:

```text
IFE 관련 내용이 어떤 PDF 어느 페이지에 있고,
관련 기능/구현 위치/디버깅 키워드는 무엇인가?
```

## 2. MVP 포함 기능

| 기능 | 설명 | 완료 기준 |
|---|---|---|
| PDF 업로드 | 사용자가 PDF 파일을 업로드 | 업로드 후 document record 생성 |
| 원본 파일 저장 | PDF 파일을 local storage에 저장 | 파일 경로가 DB에 저장됨 |
| 텍스트 추출 | 페이지별 텍스트 추출 | page table에 page text 저장 |
| 청크 생성 | 검색 가능한 단위로 분할 | chunk table에 저장 |
| 임베딩 생성 | 청크별 vector 생성 | pgvector column에 저장 |
| 벡터 검색 | 자연어 query로 관련 청크 검색 | top-k 결과 반환 |
| 간단한 요약 | 문서/청크 요약 생성 | summary field 저장 |
| 엔티티 추출 | 기술 용어 추출 | entity table 저장 |
| 기본 관계 저장 | entity와 chunk 연결 | mention/related edge 저장 |
| 원문 페이지 링크 | 검색 결과에서 PDF 페이지 확인 | document id + page number 반환 |
| 지식 카드 UI | 엔티티별 요약 표시 | entity detail 화면 표시 |

## 3. MVP 제외 또는 후순위

| 기능 | 제외 이유 |
|---|---|
| 완전 자동 OCR 고도화 | PDF 품질 차이가 커서 MVP 범위를 초과 |
| 복잡한 표 구조 해석 | 표 의미 분석은 별도 평가 필요 |
| Neo4j 도입 | 초기 관계 탐색은 PostgreSQL로 충분 |
| 실시간 협업 | 핵심 가치와 직접 관련 낮음 |
| 사용자 권한 관리 | 개인/소규모 팀 사용 가정 |
| 대규모 운영 모니터링 | MVP 단계에서는 로그 중심으로 충분 |
| 고급 그래프 추론 | 데이터가 쌓인 뒤 필요성 판단 |
| 자동 entity merge 고도화 | 초기에는 rule + LLM 보조로 처리 |

## 4. MVP 데이터 모델 최소 범위

필수 테이블:

- `documents`
- `document_pages`
- `document_chunks`
- `entities`
- `entity_mentions`
- `knowledge_nodes`
- `knowledge_edges`
- `processing_jobs`

## 5. MVP API 최소 범위

```text
POST   /api/documents/upload
GET    /api/documents
GET    /api/documents/{document_id}
GET    /api/documents/{document_id}/pages/{page_number}
GET    /api/jobs/{job_id}

POST   /api/search
GET    /api/entities
GET    /api/entities/{entity_id}
GET    /api/entities/{entity_id}/knowledge-card
GET    /api/graph/entities/{entity_id}
```

## 6. MVP 품질 기준

- PDF 10개를 연속 처리해도 서버가 중단되지 않는다.
- 처리 실패 시 job status가 `failed`로 기록된다.
- 검색 결과에는 항상 page number가 포함된다.
- LLM JSON parse 실패는 재시도하거나 raw output을 저장한다.
- 사용자는 요약 결과에서 원문 페이지로 이동할 수 있다.

