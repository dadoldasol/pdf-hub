# Graph View

이 문서는 entity graph 화면의 layout, node/edge 스타일, interaction, filtering 기준을 정의한다.

## 목표

Graph view는 "많은 연결을 보여주는 화면"이 아니라 "선택한 entity가 어떤 개념과 어떤 의미로 연결되는지 설명하는 화면"이어야 한다.

## 기본 표시 정책

- selected entity를 중심에 둔다.
- 기본 depth는 `1`이다.
- 기본 edge confidence threshold는 `0.60`이다.
- `co_mention` edge는 기본적으로 숨긴다.
- 기본 edge 수는 selected entity 기준 top-N으로 제한한다.
- 사용자가 node를 클릭하면 해당 node 중심으로 확장한다.

## Filter

필수 filter:

- node type
- edge type
- confidence threshold
- include co-mentions
- depth

우선 edge type:

- `IMPLEMENTS`
- `SUPPORTS`
- `LIMITED_BY`
- `DEBUGGED_BY`
- `CALLS`
- `DEPENDS_ON`
- `CHANGED_IN`
- `RELATED_TO`
- `MENTIONED_IN`

## Node 표현

Node에는 최소한 다음 정보를 표현한다.

- entity name
- entity type
- confidence 또는 importance
- mention count

시각 표현:

- node type별 색상 또는 icon을 구분한다.
- selected node는 명확히 강조한다.
- 너무 긴 label은 줄이되 hover/side panel에서 전체 이름을 보여준다.
- degree가 높은 node는 크기를 키울 수 있지만 layout을 망가뜨릴 정도로 커지면 안 된다.

## Edge 표현

Edge는 relation type을 설명해야 한다.

- edge type label 또는 tooltip을 제공한다.
- confidence가 낮을수록 얇거나 흐리게 표시한다.
- co-mention edge는 점선 등으로 typed relation과 구분한다.
- edge 클릭 시 evidence panel을 연다.

Evidence panel 내용:

- relation type
- confidence
- source document
- page number
- chunk id
- evidence snippet
- extraction method

## Layout 기준

Graph가 겹쳐 보이지 않도록 다음 기준을 적용한다.

- selected entity 중심 radial/force layout을 사용한다.
- 기본 표시 edge 수를 제한한다.
- node 간 최소 거리를 둔다.
- label은 node 주변에 겹치지 않도록 배치한다.
- 화면 크기에 따라 zoom/pan을 제공한다.
- 너무 복잡하면 "더 보기" 또는 expand-on-click으로 나눈다.

## Empty/Low Confidence 상태

typed relation이 아직 부족할 수 있으므로 다음 상태를 구분한다.

- 관계 없음: 저장된 relation이 없는 경우
- 낮은 confidence만 있음: threshold 때문에 숨겨진 경우
- co-mention만 있음: typed relation은 없지만 함께 언급된 경우

이 상태를 UI에서 구분해야 사용자가 graph가 비어 있는 이유를 이해할 수 있다.
