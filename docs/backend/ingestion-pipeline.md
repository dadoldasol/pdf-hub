# Ingestion Pipeline

이 문서는 PDF 업로드 이후 파일 저장, 작업 생성, 텍스트 추출, chunk 생성, embedding, rule/pattern entity 저장, 그리고 후속 LLM refinement job까지의 처리 흐름을 정의한다.

## 현재 처리 흐름

Upload ingestion은 안정성을 최우선으로 한다. API 요청은 긴 PDF 처리를 직접 수행하지 않고, worker가 별도 process에서 job을 처리한다.

```text
POST /api/documents/upload
  -> original PDF 저장
  -> documents record 생성
  -> processing_jobs record 생성
       extra_metadata.job_type = "ingestion"
  -> API request는 queued job을 반환하고 종료

worker_main
  -> queued job claim
  -> job_type이 ingestion이면 run_ingestion_job 실행
  -> page text를 페이지별 child process에서 timeout 격리 추출
  -> page 단위 document_pages/document_chunks 저장 및 commit
  -> deterministic embedding 생성
  -> rule/pattern entity 추출
  -> entity_mentions 저장
  -> ingestion completed 또는 partially_processed
  -> llm_refinement job 자동 생성
```

업로드 중에는 LLM을 호출하지 않는다. 긴 PDF에서 Ollama/OpenAI 호출이 ingestion 전체를 지연시키거나 DB transaction을 오래 잡는 문제를 막기 위해서다.

## 후속 LLM Refinement 흐름

Ingestion이 끝나면 같은 document에 대해 별도 refinement job이 자동으로 queued 된다.

```text
processing_jobs
  extra_metadata.job_type = "llm_refinement"

worker_main
  -> queued job claim
  -> job_type이 llm_refinement이면 run_llm_refinement_job 실행
  -> document의 entity mentions 조회
  -> entity별 snippet evidence aggregation
  -> DB transaction 밖에서 LLM 호출
  -> entity description과 knowledge card metadata 저장
  -> entity 하나마다 commit
  -> completed / partially_processed / failed
```

저장 위치:

- `entities.description`
- `entities.confidence`
- `entities.extra_metadata["knowledge_card"]`
- `entities.extra_metadata["llm_refinement"]`

## Document Lifecycle 전처리

업로드는 ingestion job 생성 전에 중복 문서 여부를 먼저 확인한다.

```text
upload request
  -> save PDF to local storage while calculating SHA-256
  -> check documents.file_hash
  -> if duplicate:
       delete newly saved duplicate file
       return existing document with duplicate=true
  -> if new:
       create document
       create ingestion processing job
       return queued job
```

중복 기준:

- filename이 아니라 SHA-256 file content hash를 사용한다.
- 중복이면 새 page/chunk/entity/job을 만들지 않는다.
- 사용자는 기존 document로 이동할 수 있어야 한다.

삭제 흐름:

```text
DELETE /api/documents/{document_id}
  -> mark active jobs cancel_requested
  -> delete document-scoped graph edges
  -> delete entity mentions
  -> delete chunks/pages/jobs
  -> delete original PDF file
  -> delete document row
  -> remove orphan entities/nodes
```

## Job Type

현재 `processing_jobs`는 `extra_metadata.job_type`으로 작업 종류를 구분한다.

| job_type | 역할 |
|---|---|
| `ingestion` | PDF 추출, chunk, embedding, rule/pattern entity 저장 |
| `llm_refinement` | entity description과 knowledge card summary 생성/갱신 |

과거 job처럼 `job_type`이 없으면 worker는 기본적으로 `ingestion`으로 처리한다.

## Job Metadata

진행률과 디버깅을 위해 job metadata에 값을 누적한다.

Ingestion metadata:

- `job_type = "ingestion"`
- `total_pages`
- `processed_pages`
- `failed_pages`
- `timeout_pages`
- `total_chunks`
- `processed_chunks`
- `current_page`
- `current_page_chunks`
- `entity_candidates`
- `entities_accepted`
- `entities_rejected`
- `entity_mentions`
- `cancel_requested`
- `stage`

Refinement metadata:

- `job_type = "llm_refinement"`
- `total_entities`
- `processed_entities`
- `failed_entities`
- `current_entity_id`
- `current_entity_name`
- `entity_failures`
- `cancel_requested`
- `stage`

상태값:

```text
queued
claimed
extracting_pdf
chunking
embedding
extracting_knowledge
refining_entities
completed
partially_processed
failed
canceled
```

`partially_processed`는 일부 페이지 또는 일부 entity refinement가 실패했지만, 성공한 데이터는 사용할 수 있는 상태다.

## 안정성 기준

- upload API는 PDF 저장과 job 생성까지만 수행한다.
- page extraction은 child process timeout 경계 안에서 실행한다.
- page/chunk 저장은 페이지 단위로 commit한다.
- chunking은 반드시 forward progress를 보장해야 한다.
- entity extraction은 upload ingestion 중 LLM을 호출하지 않는다.
- LLM refinement는 entity 단위로 commit한다.
- LLM 호출 중 DB transaction을 오래 잡지 않는다.
- cancel 요청은 page extraction 또는 entity refinement 사이에서 확인한다.

## 다음 고도화 우선순위

1. refinement job 재처리 API 또는 CLI 추가
2. refinement prompt/model version metadata 저장
3. section-aware context aggregation
4. entity filtering/ranking 개선
5. typed relation extraction job 추가
6. graph API/UI 필터링 개선
