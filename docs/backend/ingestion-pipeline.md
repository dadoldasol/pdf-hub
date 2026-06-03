# Ingestion Pipeline

이 문서는 PDF 업로드 이후 파일 저장, 작업 생성, 텍스트 추출, chunk 생성, embedding, entity/relation 추출, knowledge card 생성까지의 처리 흐름을 정의한다.

## MVP 현재 흐름

```text
POST /api/documents/upload
  -> original PDF 저장
  -> documents record 생성
  -> processing_jobs record 생성
  -> BackgroundTasks로 ingestion worker 실행
  -> page text 추출
  -> document_pages 저장
  -> document_chunks 저장
  -> deterministic embedding 생성
  -> rule/pattern entity 추출
  -> entity_mentions 저장
  -> 검색/지식카드/그래프 API에서 조회
```

현재 흐름은 end-to-end 동작 확인에는 충분하지만, entity 품질과 graph 의미를 보장하지는 않는다.

## MVP 이후 개선 흐름

```text
1. PDF 저장 및 job 생성
2. page text 추출
3. section-aware chunking
4. chunk embedding 생성
5. entity candidate 추출
6. entity normalization/filtering/ranking
7. LLM entity validation
8. relation extraction
9. entity-centric context aggregation
10. knowledge card generation
11. graph node/edge 저장 또는 갱신
12. job 완료
```

## 손봐야 할 단계

### 1. Chunking

Knowledge card와 relation extraction 품질은 chunk 품질에 크게 의존한다. 단순 길이 기반 chunk만 사용하면 개념 설명이 끊기거나, 너무 많은 노이즈가 포함될 수 있다.

보완 기준:

- page number와 chunk id는 항상 유지한다.
- section heading, bullet, table-like block을 가능한 한 보존한다.
- entity mention 주변의 앞뒤 chunk를 context로 가져올 수 있도록 chunk index를 안정적으로 유지한다.
- 너무 짧은 chunk는 검색/LLM 입력 전에 병합 후보로 둔다.

관련 모듈:

- `backend/app/services/pdf_processing_service.py`
- `backend/app/workers/ingestion_worker.py`

### 2. Entity 정제

현재 rule/pattern 추출은 후보를 넓게 잡는 데 유리하지만, 사용자에게 그대로 노출하기에는 노이즈가 많다.

보완 기준:

- stopword/banlist를 도입한다.
- entity type별 allowlist와 validation rule을 둔다.
- mention count, page spread, source quality, confidence로 ranking한다.
- normalize key를 기준으로 중복 entity를 merge한다.
- 낮은 confidence entity는 기본 UI 목록에서 숨긴다.

관련 모듈:

- `backend/app/services/entity_extraction_service.py`
- `backend/app/services/entity_service.py`
- `backend/app/models/entity.py`

### 3. Knowledge Card 생성

Knowledge card는 원문 chunk 목록이 아니라 entity 중심 요약이어야 한다.

보완 기준:

- entity mention chunk와 주변 context를 모아 context pack을 만든다.
- LLM으로 정의, 역할, 관련 구성요소, debugging 단서, 근거를 생성한다.
- 생성 결과는 JSON schema로 검증한다.
- 근거에는 `document_id`, `page_number`, `chunk_id`를 포함한다.
- raw chunk는 카드 하단 evidence로 노출한다.

관련 모듈:

- `backend/app/services/entity_service.py`
- `backend/app/prompts/summary.md`
- `backend/app/schemas/entity.py`

### 4. Relation/Graph 생성

Graph는 co-mention edge만으로 만들면 연결 수가 많고 의미가 약하다. typed relation을 저장하고, co-mention은 보조 신호로 사용한다.

보완 기준:

- relation type과 confidence를 저장한다.
- source chunk/page/evidence snippet을 저장한다.
- graph API는 edge type, confidence, evidence를 반환한다.
- 낮은 confidence edge는 기본 graph에서 숨긴다.

관련 모듈:

- `backend/app/models/graph.py`
- `backend/app/services/graph_service.py`
- `backend/app/workers/ingestion_worker.py`

## Job Metadata

진행률과 디버깅을 위해 job metadata에 다음 값을 누적한다.

- `total_pages`
- `processed_pages`
- `total_chunks`
- `processed_chunks`
- `entity_candidates`
- `entities_saved`
- `relations_saved`
- `knowledge_cards_generated`
- `cancel_requested`
- `stage`

## 구현 우선순위

1. entity filtering/ranking 개선
2. knowledge card용 context aggregation 추가
3. LLM 기반 knowledge card 생성
4. typed relation extraction 추가
5. graph API/UI 필터링 개선
