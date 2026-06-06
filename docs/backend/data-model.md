# Backend Data Model

이 문서는 문서, 페이지, chunk, entity, graph, processing job 테이블의 데이터 모델 기준을 정의한다.

## Document Lifecycle Fields

`documents` 테이블은 중복 업로드 방지를 위해 원본 PDF hash를 저장한다.

```text
documents
- id
- title
- original_filename
- storage_path
- content_type
- file_size_bytes
- file_hash
- page_count
- status
- summary
- extra_metadata
- created_at
- updated_at
```

## File Hash

- `file_hash`는 SHA-256 hex digest이다.
- 같은 PDF 내용은 같은 `file_hash`를 가져야 한다.
- `file_hash`에는 unique index를 둔다.
- 중복 판단은 filename이 아니라 file content 기준이다.

## Delete Policy

초기 구현은 hard delete를 사용한다.

삭제 시 제거 대상:

- `processing_jobs` for document
- `entity_mentions` for document
- `knowledge_edges` whose `source_chunk_id` belongs to the document
- `document_chunks`
- `document_pages`
- `documents`
- orphan `entities`
- orphan `knowledge_nodes`

주의:

- entity는 여러 문서가 공유할 수 있으므로 특정 document 삭제 시 바로 삭제하지 않는다.
- 삭제 후 mention이 0개인 entity만 orphan cleanup 대상으로 본다.
- knowledge node도 연결된 entity가 삭제되거나 edge가 없으면 cleanup할 수 있다.

## Page Extraction Fields

`document_pages`는 페이지별 추출 결과와 실패 정보를 저장한다.

```text
document_pages
- id
- document_id
- page_number
- text
- needs_ocr
- extraction_status
- extraction_error
- extraction_seconds
- extra_metadata
- created_at
```

`extraction_status` 값:

- `completed`: 텍스트 추출 성공
- `timeout`: 페이지별 timeout 초과
- `failed`: 추출 중 예외 발생

timeout/failed 페이지도 row를 남긴다. 이 경우 `text`는 빈 문자열일 수 있고, `needs_ocr=true`로 후속 재처리 후보임을 표시한다.

## Reprocess Policy

현재 worker는 기존 성공 페이지를 먼저 삭제하지 않는다. 같은 job을 재실행하면 `extraction_status=completed`인 페이지는 건너뛰고, 실패/미처리 페이지만 이어서 처리한다.

향후 명시적 reprocess API는 document row와 original PDF file은 유지하고, 다음 데이터를 재생성한다.

- `document_pages`
- `document_chunks`
- `entity_mentions`
- document-scoped `knowledge_edges`
- job row

명시적 reprocess를 구현할 때도 기존 성공 데이터를 먼저 전체 삭제하지 않고, 새 run 결과가 저장된 뒤 성공 범위를 교체하는 방식을 우선 검토한다.

## Migration Notes

`documents.file_hash`를 추가할 때 기존 row가 있을 수 있다. 운영 데이터가 있는 경우 migration 이후 별도 backfill이 필요하다.

초기 로컬 개발 환경에서는 다음 중 하나를 선택한다.

- 기존 DB를 유지하고 file hash backfill script를 별도 실행한다.
- 로컬 DB를 초기화하고 migration을 다시 적용한다.

이번 구현에서는 신규 업로드부터 `file_hash`를 저장한다.
