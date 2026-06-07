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
```

## 검증

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q --basetemp .\.pytest-tmp -p no:cacheprovider
.\.venv\Scripts\python.exe -m compileall -q app tests
```

주요 결과:

- Backend tests: `42 passed, 1 warning`
- Ruff: passed
- Compileall: passed

## 남은 작업

- refinement prompt/model version metadata 저장
- refinement 재처리 API 또는 CLI 추가
- entity별 context aggregation을 snippet 중심에서 section/chunk 중심으로 개선
- typed relation extraction job 추가
- frontend에서 refinement status와 evidence 중심 UI 제공
