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


def test_knowledge_card_uses_refined_metadata(db_session, document, document_chunk) -> None:
    entity = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        description="Image Front End block.",
        confidence=0.95,
        extra_metadata={
            "knowledge_card": {
                "summary": "IFE handles front-end ISP processing.",
                "features": ["Front-end image processing"],
                "implementation_locations": ["ISP pipeline"],
                "debug_keywords": ["IFE"],
                "limitations": ["Evidence is limited."],
            }
        },
    )
    try:
        db_session.add(entity)
        db_session.flush()
        db_session.add(
            EntityMention(
                entity_id=entity.id,
                document_id=document.id,
                chunk_id=document_chunk.id,
                page_number=1,
                snippet="IFE appears.",
                confidence=0.95,
                extra_metadata={},
            )
        )
        db_session.commit()

        card = EntityService(db_session).get_knowledge_card(entity.id)

        assert card.summary == "IFE handles front-end ISP processing."
        assert card.features == ["Front-end image processing"]
        assert card.implementation_locations == ["ISP pipeline"]
        assert card.debug_keywords == ["IFE"]
        assert card.limitations == ["Evidence is limited."]
    finally:
        db_session.execute(delete(EntityMention).where(EntityMention.entity_id == entity.id))
        db_session.execute(delete(Entity).where(Entity.id == entity.id))
        db_session.delete(document_chunk)
        db_session.delete(document)
        db_session.commit()
