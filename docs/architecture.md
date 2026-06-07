# 시스템 아키텍처

## 1. 전체 구조

```text
Frontend
  React 또는 Next.js
  - 문서 목록
  - 검색
  - 지식 카드
  - 엔티티 상세
  - 그래프 뷰
  - PDF 원문 링크

Backend API
  FastAPI
  - 파일 업로드
  - 문서 조회
  - 검색 API
  - 엔티티 API
  - 그래프 API
  - 작업 상태 API

Ingestion Worker
  - PDF 추출
  - 청크 생성
  - 임베딩 생성
  - rule 기반 엔티티 추출
  - 실패 페이지 기록

LLM Refinement Worker
  - ingestion 완료 후 자동 생성된 refinement job 처리
  - entity별 evidence snippet 수집
  - entity description 생성
  - knowledge card summary/details 생성
  - LLM 실패 entity 기록

Storage
  PostgreSQL + pgvector
  - 문서 메타데이터
  - 페이지
  - 청크
  - 엔티티
  - 관계
  - 임베딩

File Storage
  Local filesystem
  - 원본 PDF
  - 페이지 이미지 또는 preview
```

## 2. 데이터 흐름

```text
1. 사용자가 PDF 업로드
2. Backend가 원본 파일 저장
3. document 레코드 생성
4. queued processing job 생성
5. 별도 ingestion worker가 job claim
6. worker가 PDF 페이지별 텍스트를 child process timeout 경계 안에서 추출
7. 페이지 텍스트와 실패 상태를 page 단위로 저장
8. 청크 분할
9. 청크별 임베딩 생성
10. rule/pattern entity 추출
11. entity mention 저장
12. ingestion 완료 후 llm_refinement job 자동 생성
13. refinement worker가 entity별 LLM description/knowledge card 생성
14. Frontend에서 검색/지식 카드/그래프 조회
```

## 3. 주요 컴포넌트

| 컴포넌트 | 역할 |
|---|---|
| FastAPI App | REST API 제공 |
| PDF Processor | 텍스트, 표, 이미지 기반 여부 추출 |
| Chunker | 페이지 텍스트를 검색 가능한 단위로 분할 |
| Ingestion Worker | 안정적인 PDF 처리와 rule/pattern entity 저장 |
| LLM Refinement Worker | entity description과 knowledge card를 후처리로 생성 |
| Embedding Service | 청크와 엔티티 설명을 벡터화 |
| Search Service | 키워드/벡터/하이브리드 검색 |
| Graph Service | 엔티티 관계 저장 및 탐색 |
| Frontend | 사용자 탐색 UI 제공 |

## 4. 저장소 설계 방향

초기 MVP에서는 PostgreSQL 하나로 시작한다.

- 일반 테이블: 문서, 페이지, 청크, 엔티티, 관계
- pgvector: 청크 임베딩, 엔티티 임베딩
- JSONB: LLM 추출 결과 원본, 메타데이터

Neo4j는 다음 시점에 검토한다.

- 관계 depth 2 이상 탐색이 핵심 기능이 될 때
- 그래프 알고리즘이 필요할 때
- entity merge, community detection, centrality 분석이 필요할 때

## 5. 작업 처리 방식

PDF 처리와 LLM 호출은 요청 시간 안에 끝내지 않는다.

현재 기본값:

- API 요청에서 업로드만 처리
- 처리 작업은 별도 worker 프로세스에서 실행한다.
- worker는 PostgreSQL의 `queued` job을 polling/claim한다.
- worker는 `processing_jobs.extra_metadata.job_type`으로 `ingestion`과 `llm_refinement`를 구분한다.
- 페이지 추출은 child process로 격리하고 timeout/cancel 시 terminate한다.
- upload ingestion 중에는 LLM을 호출하지 않는다.
- LLM refinement는 ingestion 완료 후 별도 job으로 실행한다.
- LLM 호출 중에는 DB transaction을 오래 잡지 않는다.
- 일부 페이지 실패 시 문서는 `partially_processed`가 될 수 있다.
- 작업 상태는 DB에 저장

확장 시:

- Celery + Redis
- RQ + Redis
- Dramatiq

## 6. 출처 추적 원칙

모든 검색 결과와 LLM 결과는 원문 위치를 가져야 한다.

필수 출처 필드:

- `document_id`
- `source_file_name`
- `page_number`
- `chunk_id`
- `text_span` 또는 `bbox`

MVP에서는 page number와 chunk id를 우선 보존한다. bbox 기반 위치 추적은 후순위로 둔다.
