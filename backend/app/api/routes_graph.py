from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.graph import GraphResponse
from app.services.graph_service import GraphService

router = APIRouter()


@router.get("/entities/{entity_id}", response_model=GraphResponse)
def get_entity_graph(
    entity_id: UUID,
    depth: int = Query(default=1, ge=1, le=2),
    edge_type: str | None = None,
    db: Session = Depends(get_db),
) -> GraphResponse:
    return GraphService(db).get_entity_graph(entity_id, depth=depth, edge_type=edge_type)

