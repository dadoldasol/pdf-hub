from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.schemas.entity import KnowledgeCard


class EntityService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_entities(self) -> list[Entity]:
        return list(self.db.scalars(select(Entity).order_by(Entity.normalized_name.asc())))

    def get_entity(self, entity_id: UUID) -> Entity | None:
        return self.db.get(Entity, entity_id)

    def get_knowledge_card(self, entity_id: UUID) -> KnowledgeCard | None:
        entity = self.get_entity(entity_id)
        if entity is None:
            return None

        return KnowledgeCard(
            entity=entity,
            summary=entity.description,
            features=[],
            implementation_locations=[],
            debug_keywords=[],
            limitations=[],
            source_pages=[],
        )

