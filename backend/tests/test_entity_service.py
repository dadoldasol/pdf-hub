from sqlalchemy import delete

from app.models.entity import Entity, EntityMention
from app.services.entity_service import EntityService


def test_list_entities_excludes_orphans(db_session, document, document_chunk) -> None:
    sourced = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        confidence=0.95,
        extra_metadata={},
    )
    orphan = Entity(
        entity_type="ISP_BLOCK",
        name="CSID",
        normalized_name="CSID",
        confidence=0.95,
        extra_metadata={},
    )
    try:
        db_session.add_all([sourced, orphan])
        db_session.flush()
        db_session.add(
            EntityMention(
                entity_id=sourced.id,
                document_id=document.id,
                chunk_id=document_chunk.id,
                page_number=1,
                snippet="IFE appears.",
                confidence=0.95,
                extra_metadata={},
            )
        )
        db_session.commit()

        entities = EntityService(db_session).list_entities()

        assert [entity.normalized_name for entity in entities] == ["IFE"]
        assert EntityService(db_session).get_entity(orphan.id) is None
    finally:
        db_session.execute(delete(EntityMention).where(EntityMention.entity_id.in_([sourced.id, orphan.id])))
        db_session.execute(delete(Entity).where(Entity.id.in_([sourced.id, orphan.id])))
        db_session.delete(document_chunk)
        db_session.delete(document)
        db_session.commit()
