from app.models.entity import Entity, EntityMention
from app.models.graph import KnowledgeNode
from app.services.graph_service import GraphService


def test_entity_graph_returns_comention_nodes(db_session, document, document_chunk) -> None:
    ife = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        confidence=0.95,
        extra_metadata={},
    )
    csid = Entity(
        entity_type="ISP_BLOCK",
        name="CSID",
        normalized_name="CSID",
        confidence=0.95,
        extra_metadata={},
    )
    db_session.add_all([ife, csid])
    db_session.flush()

    ife_node = KnowledgeNode(
        entity_id=ife.id,
        node_type=ife.entity_type,
        name=ife.name,
        normalized_name=ife.normalized_name,
        extra_metadata={},
    )
    csid_node = KnowledgeNode(
        entity_id=csid.id,
        node_type=csid.entity_type,
        name=csid.name,
        normalized_name=csid.normalized_name,
        extra_metadata={},
    )
    db_session.add_all([ife_node, csid_node])
    db_session.flush()

    db_session.add_all(
        [
            EntityMention(
                entity_id=ife.id,
                document_id=document.id,
                chunk_id=document_chunk.id,
                page_number=1,
                snippet="IFE and CSID are related.",
                confidence=0.95,
                extra_metadata={},
            ),
            EntityMention(
                entity_id=csid.id,
                document_id=document.id,
                chunk_id=document_chunk.id,
                page_number=1,
                snippet="IFE and CSID are related.",
                confidence=0.95,
                extra_metadata={},
            ),
        ]
    )
    db_session.flush()

    graph = GraphService(db_session).get_entity_graph(ife.id)

    assert {node.name for node in graph.nodes} == {"IFE", "CSID"}
    assert len(graph.edges) == 1
    assert graph.edges[0].source_node_id == ife_node.id
    assert graph.edges[0].target_node_id == csid_node.id
    assert graph.edges[0].edge_type == "RELATED_TO"


def test_entity_graph_filters_unsupported_edge_type(db_session, document, document_chunk) -> None:
    entity = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        confidence=0.95,
        extra_metadata={},
    )
    db_session.add(entity)
    db_session.flush()
    db_session.add(
        KnowledgeNode(
            entity_id=entity.id,
            node_type=entity.entity_type,
            name=entity.name,
            normalized_name=entity.normalized_name,
            extra_metadata={},
        )
    )
    db_session.flush()

    graph = GraphService(db_session).get_entity_graph(entity.id, edge_type="CALLS")

    assert graph.nodes == []
    assert graph.edges == []
