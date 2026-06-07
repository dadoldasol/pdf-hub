# PDF Knowledge Hub 문서

이 디렉토리는 PDF 기반 기술 문서를 분석해 지식화하는 시스템의 제품 목표, 아키텍처, 완료된 MVP 기준, 현재 고도화 계획을 정의한다.

대상 시스템은 Android Camera HAL, kernel layer, ISP block, chipset 변경사항, code flow, debugging guide 같은 전문 기술 PDF를 입력으로 받아 다음을 제공한다.

- PDF 업로드 및 텍스트 추출
- 페이지, 청크, 엔티티, 요약 결과 저장
- 벡터 검색과 키워드 검색
- 관련 개념을 묶은 지식 카드
- 엔티티 관계 기반 그래프 탐색
- 원문 PDF 페이지 출처 연결

## 문서 구조

```text
docs/
  README.md
  project-overview.md
  architecture.md
  tech-stack.md
  mvp-scope.md
  roadmap.md
  document-map.md
  implementation-plan.md
  technology-decisions.md

  backend/
    api-design.md
    data-model.md
    ingestion-pipeline.md

  pdf/
    pdf-processing.md
    ocr-strategy.md

  llm/
    extraction-pipeline.md
    prompt-design.md
    evaluation.md

  search/
    vector-search.md
    keyword-search.md
    hybrid-search.md

  graph/
    graph-model.md
    graph-query.md

  frontend/
    ui-requirements.md
    graph-view.md

  operations/
    local-dev.md
    deployment.md
    monitoring.md
```

## 우선 읽을 문서

| 순서 | 문서 | 목적 |
|---:|---|---|
| 1 | `project-overview.md` | 프로젝트 목표, 문제 정의, 범위 이해 |
| 2 | `implementation-plan.md` | 현재 구현 상태와 다음 고도화 항목 확인 |
| 3 | `architecture.md` | 전체 시스템 구성과 데이터 흐름 이해 |
| 4 | `backend/ingestion-pipeline.md` | upload ingestion과 LLM refinement job 흐름 확인 |
| 5 | `llm/extraction-pipeline.md` | entity/card LLM refinement 기준 확인 |
| 6 | `tech-stack.md` | 기술 스택과 역할 확인 |
| 7 | `mvp-scope.md` | 완료된 MVP 기준과 회귀 방지 범위 확인 |
| 8 | `technology-decisions.md` | 주요 기술 선택 기준 확인 |

## 개발 원칙

- MVP는 완료된 기준선으로 보고, 이후 작업은 실제 PDF 안정성과 지식 품질 고도화를 우선한다.
- 처음부터 완전한 엔터프라이즈 시스템을 만들지 않는다.
- PDF 원문 출처를 항상 보존한다.
- LLM 결과는 저장 전 구조화하고 검증한다.
- upload ingestion 중에는 LLM을 호출하지 않는다. LLM은 별도 refinement job에서 천천히 실행한다.
- 검색은 현재 벡터 검색을 기반으로 하고, 이후 키워드/하이브리드 검색을 강화한다.
- 그래프는 초기에는 PostgreSQL 테이블로 구현하고, 관계 탐색이 복잡해질 때 Neo4j를 검토한다.

## 완료된 MVP 기준

MVP는 다음 질문에 답할 수 있어야 한다.

> "IFE와 관련된 문서 내용을 찾아서, 요약/기능/구현 위치/디버깅 키워드/관련 페이지를 보여줘."

MVP 완료 기준:

- PDF 업로드 가능
- 페이지별 텍스트 추출 가능
- 청크 저장 가능
- 임베딩 생성 가능
- 벡터 검색 가능
- 간단한 요약 생성 가능
- 엔티티 추출 가능
- 지식 카드 UI 표시 가능
- 검색 결과에서 원문 PDF 페이지로 이동 가능

## 현재 고도화 목표

- 큰 PDF 업로드 안정성 유지
- 업로드 완료 후 자동 LLM refinement job으로 entity description과 knowledge card summary 개선
- entity ranking/filtering/merge 개선
- section-aware context aggregation
- typed relation extraction
- graph evidence/confidence 제공
- frontend에서 refinement status와 근거 중심 UI 개선
