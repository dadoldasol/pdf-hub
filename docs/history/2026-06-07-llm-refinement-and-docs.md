# 2026-06-07 LLM Refinement and Documentation Update

## 요약

큰 PDF 업로드 안정성을 유지하면서 knowledge card 품질을 높이기 위해 upload ingestion과 LLM 처리를 분리했다.

이제 upload ingestion은 PDF 추출, chunking, embedding, rule/pattern entity 저장까지만 수행한다. ingestion이 완료되면 같은 document에 대해 `llm_refinement` processing job이 자동 생성되고, 별도 worker가 entity description과 knowledge card summary/details를 천천히 갱신한다.

## 주요 결정

- upload ingestion 중에는 LLM을 호출하지 않는다.
- `processing_jobs.extra_metadata.job_type`으로 작업 종류를 구분한다.
  - `ingestion`: PDF 추출, chunk, embedding, rule/pattern entity 저장
  - `llm_refinement`: entity description과 knowledge card summary/details 생성
- LLM 호출 중 DB transaction을 오래 잡지 않는다.
- refinement 결과는 우선 `entities.description`과 `entities.extra_metadata["knowledge_card"]`에 저장한다.
- 별도 `knowledge_cards` 테이블과 versioning은 다음 고도화 단계로 둔다.

## 관련 커밋

```text
5e52d55 chore: ignore pytest temp artifacts
2f75090 feat: add post-ingestion LLM refinement
700f0a9 docs: update docs for removing MVP & history for today's work
f39ecae feat: add manual refinement reprocessing
```

## 추가 작업: Manual Refinement Reprocessing

기존 문서의 LLM refinement를 다시 실행할 수 있도록 수동 재처리 API를 추가했다.

새 API:

```text
POST /api/documents/{document_id}/refine
```

요청 body:

```json
{
  "force": false
}
```

동작 정책:

- document가 없으면 `404`.
- active `llm_refinement` job이 있으면 새 job을 만들지 않고 기존 job을 반환한다.
- 완료/실패/취소된 refinement job이 있고 `force=false`이면 최신 refinement job을 반환한다.
- `force=true`이면 완료/실패/취소된 refinement job 이후 새 job을 queue한다.

함께 반영한 개선:

- refinement 결과 metadata에 provider, model, prompt_version을 저장한다.
- `KnowledgeRefinementService.PROMPT_VERSION = "knowledge_refinement.v1"`를 추가했다.
- API, service, worker, docs 테스트를 보강했다.

## 검증

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q --basetemp .\.pytest-tmp -p no:cacheprovider
.\.venv\Scripts\python.exe -m compileall -q app tests
```

주요 결과:

- Backend tests: `46 passed, 1 warning`
- Ruff: passed
- Compileall: passed

## 남은 작업

- entity별 context aggregation을 snippet 중심에서 section/chunk 중심으로 개선한다.
- entity filtering/ranking을 개선한다.
  - stopword/banlist 확장
  - entity type별 allowlist 보강
  - mention count, page spread, confidence 기반 ranking
- refinement status를 frontend에 노출한다.
  - 문서 목록 또는 문서 상세에서 ingestion/refinement 상태를 구분
  - refinement 진행 중/완료/부분 실패 표시
- refinement 재처리 UI 또는 CLI를 추가한다.
  - 현재 API는 있으나 frontend action은 없다.
- refinement 결과 versioning을 별도 table로 승격할지 검토한다.
  - prompt/model별 이력
  - 이전 card와 새 card 비교
  - 재처리 실패 시 rollback 기준
- typed relation extraction job을 추가한다.
  - `IMPLEMENTS`, `SUPPORTS`, `LIMITED_BY`, `DEBUGGED_BY`, `CALLS`, `DEPENDS_ON`, `RELATED_TO`
  - source chunk/page/evidence snippet 저장
- graph API/UI를 confidence, edge type, evidence 중심으로 개선한다.
- 실제 PDF end-to-end로 재검증한다.
  - upload ingestion 완료 시간
  - 자동 refinement job 생성 여부
  - manual `POST /api/documents/{document_id}/refine` 재처리
  - knowledge card summary 품질
