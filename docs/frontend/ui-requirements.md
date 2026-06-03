# UI Requirements

이 문서는 문서 목록, 업로드, 검색, entity 목록, knowledge card, entity detail, graph view 화면의 요구사항을 정의한다.

## MVP 이후 UX 문제

브라우저 검증 결과, entity/knowledge card/graph 화면에서 다음 문제가 확인되었다.

- 필요하지 않은 entity가 많이 노출된다.
- knowledge card가 chunk 원문 중심이라 개념을 이해하기 어렵다.
- graph 연결이 너무 많고 겹치며, 연결의 의미를 알기 어렵다.

UI는 backend pipeline 개선과 함께 사용자가 "무엇을 볼 가치가 있는지"를 판단할 수 있게 도와야 한다.

## Entity 목록

Entity 목록은 모든 후보를 나열하지 않고, 탐색 가치가 높은 entity를 우선 보여준다.

요구사항:

- type filter를 제공한다.
- mention count, page count, confidence를 표시한다.
- 낮은 confidence entity는 기본적으로 숨긴다.
- 검색어로 entity 이름과 type을 필터링할 수 있다.
- entity type별 시각적 구분을 제공한다.
- stopword/low quality entity가 보여도 사용자가 제외 후보로 판단할 수 있는 근거를 보여준다.

기본 정렬:

```text
confidence desc
  -> page spread desc
  -> mention count desc
  -> name asc
```

## Knowledge Card

Knowledge card는 chunk 원문보다 개념 요약을 먼저 보여준다.

요구사항:

- entity 이름, type, confidence를 상단에 표시한다.
- 정의, 역할, 관련 구성요소, 구현 위치, debugging 단서를 구조화해서 보여준다.
- 근거 page/chunk 링크를 제공한다.
- 근거가 약한 내용은 불확실하다고 표시한다.
- 원문 chunk는 접을 수 있는 evidence 영역에 둔다.
- 사용자가 원문 PDF page로 이동할 수 있어야 한다.

권장 섹션:

- `Definition`
- `Role`
- `Related Components`
- `Implementation Clues`
- `Debugging Clues`
- `Evidence`

## Graph View

Graph는 기본적으로 작고 설명 가능해야 한다. 모든 연결을 한 번에 보여주는 방식은 피한다.

요구사항:

- 기본 depth는 `1`로 제한한다.
- 기본 edge threshold는 confidence `0.60` 이상으로 한다.
- edge type filter를 제공한다.
- co-mention edge는 기본적으로 숨기거나 별도 toggle로 제공한다.
- node type별 색상/아이콘을 구분한다.
- edge label 또는 tooltip으로 relation type을 보여준다.
- edge 클릭 시 source page, chunk, evidence snippet을 보여준다.
- degree가 높은 node는 자동으로 접거나 top-N edge만 보여준다.
- 사용자가 node를 클릭하면 주변 관계를 점진적으로 확장한다.

Graph가 복잡해지는 경우:

- top-N 관계만 우선 표시한다.
- confidence가 낮은 edge를 숨긴다.
- 같은 type의 반복 edge를 그룹화한다.
- selected entity 중심 layout을 유지한다.

## Backend 응답 요구사항

UI 개선을 위해 API 응답에는 다음 정보가 필요하다.

Entity:

- `entity_id`
- `name`
- `normalized_name`
- `entity_type`
- `confidence`
- `mention_count`
- `page_count`
- `source_pages`

Knowledge card:

- `summary`
- `definition`
- `role`
- `related_components`
- `implementation_clues`
- `debugging_clues`
- `evidence`
- `uncertainties`

Graph edge:

- `edge_type`
- `confidence`
- `source_page_number`
- `source_chunk_id`
- `evidence_snippet`
- `extraction_method`

## 구현 우선순위

1. entity 목록에 confidence/type/mention 기반 필터를 추가한다.
2. knowledge card를 구조화된 요약 중심으로 바꾼다.
3. graph view에 edge type/confidence filter를 추가한다.
4. edge tooltip 또는 side panel로 관계 근거를 보여준다.
5. graph layout이 복잡할 때 top-N/expand-on-click 방식으로 제한한다.
