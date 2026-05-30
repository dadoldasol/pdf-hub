from uuid import UUID

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: UUID
    node_type: str
    name: str
    description: str | None = None


class GraphEdge(BaseModel):
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: str
    confidence: float | None = None


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

