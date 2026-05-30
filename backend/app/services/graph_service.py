from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.graph import GraphResponse


class GraphService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_entity_graph(self, entity_id: UUID, depth: int = 1, edge_type: str | None = None) -> GraphResponse:
        return GraphResponse(nodes=[], edges=[])

