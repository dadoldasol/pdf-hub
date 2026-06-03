from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.entity import Entity, EntityMention
from app.schemas.entity import KnowledgeCard


class EntityService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_entities(self) -> list[Entity]:
        mention_count = func.count(EntityMention.id).label("mention_count")
        stmt = (
            select(Entity)
            .outerjoin(EntityMention, EntityMention.entity_id == Entity.id)
            .group_by(Entity.id)
            .order_by(desc(Entity.confidence).nullslast(), desc(mention_count), Entity.normalized_name.asc())
        )
        return list(self.db.scalars(stmt))

    def get_entity(self, entity_id: UUID) -> Entity | None:
        return self.db.get(Entity, entity_id)

    def get_knowledge_card(self, entity_id: UUID) -> KnowledgeCard | None:
        entity = self.get_entity(entity_id)
        if entity is None:
            return None

        mention_rows = (
            self.db.query(EntityMention, Document.title)
            .join(Document, Document.id == EntityMention.document_id)
            .filter(EntityMention.entity_id == entity_id)
            .order_by(EntityMention.created_at.desc())
            .limit(20)
            .all()
        )
        source_pages = [
            {
                "document_id": mention.document_id,
                "document_title": document_title,
                "page_number": mention.page_number,
                "chunk_id": mention.chunk_id,
                "snippet": mention.snippet,
                "confidence": mention.confidence,
            }
            for mention, document_title in mention_rows
        ]

        return KnowledgeCard(
            entity=entity,
            summary=entity.description or self._fallback_summary(entity, len(source_pages)),
            features=[],
            implementation_locations=[],
            debug_keywords=[],
            limitations=[],
            source_pages=source_pages,
        )

    def _fallback_summary(self, entity: Entity, mention_count: int) -> str:
        return f"{entity.name} is a {entity.entity_type} entity found in {mention_count} source page(s)."
