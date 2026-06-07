# Backend API Design

이 문서는 backend API 계약과 주요 응답 정책을 정의한다.

## Document Lifecycle

Post-MVP부터 문서는 단순 업로드 대상이 아니라 lifecycle을 가진 리소스로 관리한다.

```text
upload
  -> deduplicate
  -> process
  -> refine
  -> list/detail/search
  -> delete
  -> reprocess (future)
```

## Documents

### Upload

```text
POST /api/documents/upload
```

동작:

1. PDF 파일을 임시 저장하지 않고 storage에 저장하면서 SHA-256 hash를 계산한다.
2. 같은 `file_hash`를 가진 기존 document가 있으면 새 ingestion job을 만들지 않는다.
3. 중복이 아니면 document와 processing job을 생성하고 ingestion worker를 실행한다.

응답:

```json
{
  "document_id": "uuid",
  "job_id": "uuid or null",
  "status": "queued | completed | already_exists",
  "duplicate": false,
  "duplicate_of_document_id": null
}
```

중복 업로드 응답:

```json
{
  "document_id": "existing-document-id",
  "job_id": null,
  "status": "already_exists",
  "duplicate": true,
  "duplicate_of_document_id": "existing-document-id"
}
```

### List

```text
GET /api/documents
```

삭제된 문서는 hard delete 정책이므로 응답에 포함되지 않는다.

### Detail

```text
GET /api/documents/{document_id}
```

존재하지 않는 document는 `404`를 반환한다.

### Page

```text
GET /api/documents/{document_id}/pages/{page_number}
```

존재하지 않는 page는 `404`를 반환한다.

### Refine

```text
POST /api/documents/{document_id}/refine
```

기존 document에 대해 LLM refinement job을 수동으로 queue한다. Upload ingestion 완료 후 refinement job은 자동 생성되지만, prompt/model 변경이나 실패 복구를 위해 수동 재처리가 필요할 수 있다.

요청:

```json
{
  "force": false
}
```

응답:

```json
{
  "document_id": "uuid",
  "job_id": "uuid",
  "status": "queued",
  "duplicate": false
}
```

정책:

- document가 없으면 `404`.
- `queued`, `claimed`, `refining_entities` 등 실행 중인 refinement job이 있으면 새 job을 만들지 않고 기존 job을 반환한다.
- 완료/실패/취소된 refinement job이 있고 `force=false`이면 최신 refinement job을 반환한다.
- `force=true`이면 완료/실패/취소된 refinement job 이후 새 refinement job을 queue한다.

### Delete

```text
DELETE /api/documents/{document_id}
```

초기 구현은 hard delete를 사용한다.

삭제 대상:

- original PDF file
- `processing_jobs`
- `entity_mentions`
- `knowledge_edges` with source chunks from the document
- `document_chunks`
- `document_pages`
- `documents`
- orphan `entities`
- orphan `knowledge_nodes`

응답:

```json
{
  "document_id": "uuid",
  "deleted": true
}
```

정책:

- document가 없으면 `404`.
- processing 중인 document도 삭제 요청을 허용한다.
- BackgroundTasks 기반 worker가 이미 실행 중일 수 있으므로, 삭제 전에 관련 job metadata에 cancel request를 기록한 뒤 cleanup한다.
- worker와 삭제가 동시에 충돌할 수 있는 경우 worker는 실패할 수 있으나, 사용자가 삭제한 document는 목록에 남지 않아야 한다.

### Reprocess

```text
POST /api/documents/{document_id}/reprocess
```

Future work. 기존 PDF 파일은 유지하고 pages/chunks/entity_mentions를 재생성한다. Entity extraction, knowledge card, graph logic이 개선된 뒤 기존 문서를 다시 처리하는 용도로 사용한다.

## Jobs

```text
GET  /api/jobs/{job_id}
POST /api/jobs/{job_id}/cancel
```

Cancel은 cooperative cancellation이다. 긴 PDF 추출 호출이 진행 중인 경우 해당 호출이 끝난 뒤 cancel 상태가 반영될 수 있다.

## Search, Entities, Graph

현재 API:

```text
POST /api/search
GET  /api/entities
GET  /api/entities/{entity_id}
GET  /api/entities/{entity_id}/knowledge-card
GET  /api/graph/entities/{entity_id}
```

문서 삭제 후 search/entity/graph 응답은 삭제된 document의 chunk/page/source를 반환하면 안 된다.
