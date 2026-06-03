# Graph Model

이 문서는 entity 관계 graph의 node, edge, relation taxonomy, confidence, source evidence 기준을 정의한다.

## 현재 MVP 한계

현재 graph는 주로 같은 chunk에 같이 등장한 entity를 연결하는 co-mention 방식이다. 이 방식은 빠르게 graph를 만들 수 있지만 다음 문제가 있다.

- edge 수가 너무 많아진다.
- 연결 의미를 설명하기 어렵다.
- 중요한 관계와 우연한 동시 등장 관계가 섞인다.
- graph layout이 쉽게 겹치고 읽기 어려워진다.

MVP 이후 graph는 co-mention 중심에서 typed relation 중심으로 이동한다.

## Node

기본 node는 `knowledge_nodes`에 저장한다.

필수 속성:

- `id`
- `node_type`
- `name`
- `normalized_name`
- `description`
- `metadata`

우선 node type:

- `ISP_BLOCK`
- `CAMERA_HAL`
- `KERNEL_DRIVER`
- `CHIPSET`
- `CODE_FILE`
- `FUNCTION`
- `DEBUG_KEYWORD`
- `FEATURE`
- `LIMITATION`
- `CALL_FLOW`
- `REGISTER`
- `CLOCK`
- `BANDWIDTH`

## Edge

기본 edge는 `knowledge_edges`에 저장한다.

필수 속성:

- `id`
- `source_node_id`
- `target_node_id`
- `edge_type`
- `confidence`
- `source_chunk_id`
- `metadata`

`metadata`에 포함할 값:

- `source_document_id`
- `source_page_number`
- `evidence_snippet`
- `extraction_method`: `rule`, `llm`, `co_mention`
- `prompt_version`
- `is_inferred`

## Relation Taxonomy

우선 relation type:

- `IMPLEMENTS`: source가 target을 구현한다.
- `SUPPORTS`: source가 target 기능을 지원한다.
- `LIMITED_BY`: source가 target 제약을 받는다.
- `DEBUGGED_BY`: source 문제를 target keyword/log로 디버깅할 수 있다.
- `CALLS`: source function/module이 target을 호출한다.
- `DEPENDS_ON`: source가 target에 의존한다.
- `CHANGED_IN`: source가 특정 chipset/version/change와 관련된다.
- `RELATED_TO`: 명확한 relation type은 없지만 의미상 관련된다.
- `MENTIONED_IN`: source가 특정 chunk/page에서 언급된다.

## Co-mention 처리 기준

Co-mention은 완전히 버리지 않고 보조 신호로 사용한다.

- 기본 graph에서는 낮은 confidence edge로 취급한다.
- typed relation이 있는 경우 typed relation을 우선한다.
- co-mention edge만 많은 node는 기본 view에서 접거나 숨긴다.
- 사용자가 `include_co_mentions=true`를 선택한 경우에만 넓게 보여준다.

## Confidence 기준

초기 기준:

- `0.85` 이상: LLM 또는 rule이 명확한 evidence와 함께 추출한 관계
- `0.60` 이상: evidence는 있으나 relation type 확신이 낮은 관계
- `0.40` 이하: co-mention 또는 약한 추론

기본 UI threshold는 `0.60` 이상으로 시작한다.

## Graph API 응답 보완

Graph API는 단순 nodes/edges 외에 edge 설명에 필요한 정보를 반환해야 한다.

```json
{
  "nodes": [],
  "edges": [
    {
      "id": "edge-id",
      "source": "node-id",
      "target": "node-id",
      "edge_type": "DEPENDS_ON",
      "confidence": 0.82,
      "source_page_number": 12,
      "source_chunk_id": "chunk-id",
      "evidence_snippet": "..."
    }
  ]
}
```

## 구현 우선순위

1. `knowledge_edges`에 typed relation과 evidence를 저장한다.
2. `GraphService`에서 edge type/confidence/source 기반 필터를 지원한다.
3. co-mention edge는 기본 graph에서 제한한다.
4. frontend graph view에서 edge type과 evidence를 설명한다.
