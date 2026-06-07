# LLM Extraction Pipeline

이 문서는 PDF에서 추출한 page/chunk 텍스트를 entity description, knowledge card, relation으로 정제하는 LLM pipeline을 정의한다.

## 현재 상태

MVP 기본 흐름은 완료되었다. 현재 시스템은 PDF 업로드, page text extraction, chunking, deterministic embedding, rule/pattern entity extraction, search, knowledge card, co-mention graph를 제공한다.

큰 PDF 안정성 문제를 줄이기 위해 LLM 호출은 upload ingestion에서 분리되었다.

현재 동작:

```text
upload ingestion
  -> PDF 저장
  -> page text extraction
  -> chunking
  -> embedding
  -> rule/pattern entity extraction
  -> entity_mentions 저장
  -> ingestion completed/partially_processed
  -> llm_refinement job 자동 queued

llm_refinement worker
  -> document의 entity mentions 조회
  -> entity별 evidence snippet aggregation
  -> LLM으로 entity description과 knowledge card 생성
  -> entities.description 갱신
  -> entities.extra_metadata["knowledge_card"] 저장
  -> refinement completed/partially_processed
```

중요한 원칙:

- upload ingestion 중에는 LLM을 호출하지 않는다.
- LLM refinement는 별도 `processing_jobs.extra_metadata.job_type = "llm_refinement"` job으로 실행한다.
- LLM 호출 중 DB transaction을 오래 잡지 않는다.
- LLM 결과는 JSON schema 기반으로 파싱한다.
- 원문 근거는 `document_id`, `page_number`, `chunk_id`, snippet으로 보존한다.

## 현재 구현 위치

| 영역 | 파일 |
|---|---|
| rule/pattern entity extraction | `backend/app/services/entity_extraction_service.py` |
| ingestion job | `backend/app/workers/ingestion_worker.py` |
| refinement job routing | `backend/app/workers/worker_main.py` |
| refinement worker | `backend/app/workers/refinement_worker.py` |
| LLM card generation client | `backend/app/services/knowledge_refinement_service.py` |
| knowledge card response | `backend/app/services/entity_service.py` |
| entity/card schema | `backend/app/schemas/entity.py` |

## Refinement Output

현재 `llm_refinement` job은 entity 단위로 다음 값을 생성한다.

```json
{
  "accepted": true,
  "description": "Entity definition grounded in evidence.",
  "summary": "Knowledge card summary.",
  "features": [],
  "implementation_locations": [],
  "debug_keywords": [],
  "limitations": [],
  "confidence": 0.9,
  "rejection_reason": ""
}
```

저장 위치:

- `entities.description`: entity 설명
- `entities.confidence`: LLM confidence가 있으면 갱신
- `entities.extra_metadata["knowledge_card"]`: summary, features, implementation locations, debug keywords, limitations
- `entities.extra_metadata["llm_refinement"]`: accepted, confidence, provider, model, prompt_version, refined_at, source_snippet_count

현재는 별도 `knowledge_cards` 테이블을 만들지 않고 JSONB metadata를 사용한다. versioning, prompt/model 이력, card 재생성 이력이 중요해지면 별도 테이블로 승격한다.

## Manual Refinement

Upload 완료 후 refinement job은 자동 생성된다. 기존 문서에 대해 refinement를 다시 실행해야 할 때는 다음 API를 사용한다.

```text
POST /api/documents/{document_id}/refine
```

기본 정책:

- active refinement job이 있으면 새 job을 만들지 않고 기존 job을 반환한다.
- 완료된 refinement job이 있으면 기본적으로 기존 job을 반환한다.
- `{"force": true}`를 보내면 완료/실패/취소된 refinement 이후 새 job을 queue한다.

## Entity 정제 방향

목표는 "문서에 등장한 토큰"이 아니라 "사용자가 탐색할 가치가 있는 기술 개념"만 entity로 남기는 것이다.

보완 기준:

- 일반 단어, 문서 구조 단어, 너무 짧거나 숫자성인 토큰은 제외한다.
- entity type별 허용 규칙을 둔다. 예: `ISP_BLOCK`, `CAMERA_HAL`, `KERNEL_DRIVER`, `CHIPSET`, `CODE_FILE`, `FUNCTION`, `DEBUG_KEYWORD`, `FEATURE`, `REGISTER`.
- mention count, page spread, source chunk 품질, confidence를 ranking에 반영한다.
- 같은 개념의 다른 표기를 normalize/merge한다. 예: `IFE`, `Image Front End`, `image front-end`.
- LLM refinement는 entity description/card 품질 개선을 담당하고, upload ingestion의 entity persistence를 막지 않는다.

## Knowledge Card 생성 방향

Knowledge card는 chunk 목록이 아니라 entity 중심의 개념 설명이어야 한다. 원문 chunk는 카드의 본문이 아니라 근거로 제공한다.

카드에 포함할 최소 구조:

- 정의: 이 entity가 무엇인지
- 역할: camera/ISP/kernel/HAL flow에서 어떤 역할을 하는지
- 관련 구성요소: 연결된 block, function, driver, register, feature
- 구현 위치: 관련 code file, function, module 단서
- debugging 단서: log keyword, limitation, common issue
- 근거: `document_id`, `page_number`, `chunk_id`, snippet
- 불확실성: 근거가 약하거나 추론인 내용 표시

현재 구현은 entity mention snippet 최대 12개를 evidence로 사용한다. 다음 단계에서는 section-aware context pack을 만들고, source chunk id 목록과 prompt/model version을 함께 저장한다.

## Relation 추출 방향

Graph는 co-mention만으로 만들면 edge가 너무 많고 의미가 약하다. 다음 고도화에서는 typed relation을 우선 저장하고, co-mention은 보조 신호로 낮은 confidence를 부여한다.

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

## 다음 우선순위

1. entity별 context aggregation을 snippet 중심에서 chunk/section 중심으로 개선한다.
2. confidence 낮은 entity/card를 UI에서 구분한다.
3. typed relation extraction job을 추가한다.
4. graph API가 confidence, edge type, source evidence를 반환하게 한다.
5. refinement 결과를 별도 table로 승격해 prompt/model별 이력을 관리한다.
