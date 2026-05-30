from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import EntityMention
from app.models.graph import KnowledgeNode
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse


class GraphService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_entity_graph(self, entity_id: UUID, depth: int = 1, edge_type: str | None = None) -> GraphResponse:
        if edge_type is not None and edge_type != "RELATED_TO":
            return GraphResponse(nodes=[], edges=[])

        source_node = self._get_node_for_entity(entity_id)
        if source_node is None:
            return GraphResponse(nodes=[], edges=[])

        related_nodes = self._get_related_nodes(entity_id)
        nodes = [self._to_graph_node(source_node)]
        edges: list[GraphEdge] = []

        for node in related_nodes:
            if node.id == source_node.id:
                continue
            nodes.append(self._to_graph_node(node))
            edges.append(
                GraphEdge(
                    id=self._virtual_edge_id(source_node.id, node.id, "RELATED_TO"),
                    source_node_id=source_node.id,
                    target_node_id=node.id,
                    edge_type="RELATED_TO",
                    confidence=0.6,
                )
            )

        return GraphResponse(nodes=nodes, edges=edges)

    def _get_node_for_entity(self, entity_id: UUID) -> KnowledgeNode | None:
        return self.db.scalar(select(KnowledgeNode).where(KnowledgeNode.entity_id == entity_id))

    def _get_related_nodes(self, entity_id: UUID) -> list[KnowledgeNode]:
        chunk_ids = list(
            self.db.scalars(
                select(EntityMention.chunk_id)
                .where(EntityMention.entity_id == entity_id, EntityMention.chunk_id.is_not(None))
                .distinct()
            )
        )
        if not chunk_ids:
            return []

        related_entity_ids = list(
            self.db.scalars(
                select(EntityMention.entity_id)
                .where(
                    EntityMention.chunk_id.in_(chunk_ids),
                    EntityMention.entity_id != entity_id,
                )
                .distinct()
            )
        )
        if not related_entity_ids:
            return []

        return list(
            self.db.scalars(
                select(KnowledgeNode)
                .where(KnowledgeNode.entity_id.in_(related_entity_ids))
                .order_by(KnowledgeNode.normalized_name.asc())
            )
        )

    def _to_graph_node(self, node: KnowledgeNode) -> GraphNode:
        return GraphNode(
            id=node.id,
            node_type=node.node_type,
            name=node.name,
            description=node.description,
        )

    def _virtual_edge_id(self, source_node_id: UUID, target_node_id: UUID, edge_type: str) -> UUID:
        key = f"{source_node_id}:{target_node_id}:{edge_type}"
        return uuid5(NAMESPACE_URL, key)
