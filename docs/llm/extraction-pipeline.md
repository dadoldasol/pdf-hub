# LLM Extraction Pipeline

이 문서는 PDF에서 추출한 page/chunk 텍스트를 entity, relation, summary, knowledge card로 정제하는 LLM pipeline을 정의한다.

## 현재 MVP 한계

현재 MVP는 PDF 업로드부터 chunk, embedding, 검색, rule/pattern 기반 entity 추출, 간단한 knowledge card, co-mention graph까지의 기본 흐름을 제공한다. 실제 PDF를 확인하면 다음 문제가 드러난다.

- 필요하지 않은 entity 후보가 많이 노출된다.
- knowledge card가 entity가 포함된 chunk 원문에 가깝기 때문에 개념을 이해하기 어렵다.
- graph edge가 co-mention 중심이라 연결은 많지만 관계 의미를 설명하기 어렵다.

MVP 이후에는 단순 추출 결과를 그대로 보여주는 방식에서, entity와 relation을 검증하고 요약하는 지식 정제 pipeline으로 확장한다.

## 개선 Pipeline

```text
PDF page text
  -> section-aware chunking
  -> entity candidate extraction
  -> entity normalization and filtering
  -> LLM entity validation
  -> relation extraction with typed edges
  -> entity-centric context aggregation
  -> knowledge card generation
  -> searchable evidence and graph response
```

## Entity 정제

목표는 "문서에 등장한 토큰"이 아니라 "사용자가 탐색할 가치가 있는 기술 개념"만 entity로 남기는 것이다.

보완 기준:

- 일반 단어, 문서 구조 단어, 너무 짧거나 숫자성인 토큰은 제외한다.
- entity type별 허용 규칙을 둔다. 예: `ISP_BLOCK`, `CAMERA_HAL`, `KERNEL_DRIVER`, `CHIPSET`, `CODE_FILE`, `FUNCTION`, `DEBUG_KEYWORD`, `FEATURE`, `REGISTER`.
- mention count, page spread, source chunk 품질, confidence를 ranking에 반영한다.
- 같은 개념의 다른 표기를 normalize/merge한다. 예: `IFE`, `Image Front End`, `image front-end`.
- LLM validation 단계에서 "기술 개념인지", "어떤 type인지", "근거 chunk가 충분한지"를 JSON schema로 검증한다.

관련 구현 위치:

- `backend/app/services/entity_extraction_service.py`
- `backend/app/workers/ingestion_worker.py`
- `backend/app/services/entity_service.py`
- `backend/app/models/entity.py`

## Knowledge Card 생성

Knowledge card는 chunk 목록이 아니라 entity 중심의 개념 설명이어야 한다. 원문 chunk는 카드의 본문이 아니라 근거로 제공한다.

카드에 포함할 최소 구조:

- 정의: 이 entity가 무엇인지
- 역할: camera/ISP/kernel/HAL flow에서 어떤 역할을 하는지
- 관련 구성요소: 연결된 block, function, driver, register, feature
- 구현 위치: 관련 code file, function, module 단서
- debugging 단서: log keyword, limitation, common issue
- 근거: `document_id`, `page_number`, `chunk_id`, snippet
- 불확실성: 근거가 약하거나 추론인 내용 표시

생성 방식:

1. entity mention이 포함된 chunk를 모은다.
2. 필요하면 앞뒤 chunk나 같은 section의 chunk를 함께 가져온다.
3. 중복 문맥을 줄이고, source id를 유지한 context pack을 만든다.
4. LLM으로 JSON schema 기반 card를 생성한다.
5. 생성 결과를 저장하고, UI에서는 원문보다 요약과 근거를 우선 보여준다.

관련 구현 위치:

- `backend/app/services/entity_service.py`
- `backend/app/schemas/entity.py`
- `backend/app/prompts/summary.md`
- `backend/app/prompts/entity_extraction.md`

## Relation 추출

Graph는 co-mention만으로 만들면 edge가 너무 많고 의미가 약하다. MVP 이후에는 typed relation을 우선 저장하고, co-mention은 보조 신호로 낮은 confidence를 부여한다.

우선 relation type:

- `IMPLEMENTS`
- `SUPPORTS`
- `LIMITED_BY`
- `DEBUGGED_BY`
- `CALLS`
- `DEPENDS_ON`
- `CHANGED_IN`
- `RELATED_TO`
- `MENTIONED_IN`

각 relation은 다음 정보를 가져야 한다.

- source entity
- target entity
- relation type
- confidence
- source chunk id
- source page number
- evidence snippet
- extraction method: `rule`, `llm`, `co_mention`

관련 구현 위치:

- `backend/app/models/graph.py`
- `backend/app/services/graph_service.py`
- `backend/app/workers/ingestion_worker.py`

## MVP 이후 우선순위

1. entity filtering/ranking을 먼저 개선한다.
2. entity별 context aggregation을 추가한다.
3. knowledge card를 LLM 요약 기반으로 생성한다.
4. typed relation extraction을 추가한다.
5. graph API가 confidence, edge type, source evidence를 반환하게 한다.
6. UI에서 entity filter, card summary, graph edge filter를 제공한다.
