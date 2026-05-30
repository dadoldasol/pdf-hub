from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.entity import EntityDetail, EntityListItem, KnowledgeCard
from app.services.entity_service import EntityService

router = APIRouter()


@router.get("", response_model=list[EntityListItem])
def list_entities(db: Session = Depends(get_db)) -> list[EntityListItem]:
    return EntityService(db).list_entities()


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(entity_id: UUID, db: Session = Depends(get_db)) -> EntityDetail:
    entity = EntityService(db).get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")
    return entity


@router.get("/{entity_id}/knowledge-card", response_model=KnowledgeCard)
def get_knowledge_card(entity_id: UUID, db: Session = Depends(get_db)) -> KnowledgeCard:
    card = EntityService(db).get_knowledge_card(entity_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Entity not found.")
    return card

