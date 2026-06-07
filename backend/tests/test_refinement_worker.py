from sqlalchemy import delete

from app.models.chunk import DocumentChunk
from app.models.entity import Entity, EntityMention
from app.models.job import ProcessingJob
from app.services.knowledge_refinement_service import KnowledgeCardRefinement
from app.workers import refinement_worker
from app.workers.refinement_worker import run_llm_refinement_job


def test_refinement_worker_updates_entity_description_and_knowledge_card(
    db_session,
    document,
    document_chunk,
    monkeypatch,
) -> None:
    entity = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        confidence=0.55,
        extra_metadata={},
    )
    db_session.add(entity)
    db_session.flush()
    mention = EntityMention(
        entity_id=entity.id,
        document_id=document.id,
        chunk_id=document_chunk.id,
        page_number=1,
        snippet="IFE is the Image Front End block in the ISP pipeline.",
        confidence=0.95,
        extra_metadata={},
    )
    job = ProcessingJob(
        document_id=document.id,
        status="queued",
        extra_metadata={"job_type": "llm_refinement"},
    )
    db_session.add_all([mention, job])
    db_session.commit()

    class FakeKnowledgeRefinementService:
        provider = "ollama"
        model = "test-model"
        PROMPT_VERSION = "test-prompt-v1"

        def refine_entity(self, *, name, entity_type, snippets):  # noqa: ANN001
            assert name == "IFE"
            assert entity_type == "ISP_BLOCK"
            assert snippets == ["IFE is the Image Front End block in the ISP pipeline."]
            return KnowledgeCardRefinement(
                accepted=True,
                description="Image Front End block in the ISP pipeline.",
                summary="IFE handles front-end ISP processing.",
                features=["Front-end image processing"],
                implementation_locations=["ISP pipeline"],
                debug_keywords=["IFE"],
                limitations=["Evidence is limited to uploaded snippets."],
                confidence=0.91,
            )

    monkeypatch.setattr(refinement_worker, "KnowledgeRefinementService", FakeKnowledgeRefinementService)

    try:
        run_llm_refinement_job(job.id)

        db_session.refresh(entity)
        db_session.refresh(job)

        assert job.status == "completed"
        assert job.extra_metadata["processed_entities"] == 1
        assert job.extra_metadata["failed_entities"] == 0
        assert entity.description == "Image Front End block in the ISP pipeline."
        assert entity.confidence == 0.91
        assert entity.extra_metadata["knowledge_card"]["summary"] == "IFE handles front-end ISP processing."
        assert entity.extra_metadata["knowledge_card"]["features"] == ["Front-end image processing"]
        assert entity.extra_metadata["llm_refinement"]["accepted"] is True
        assert entity.extra_metadata["llm_refinement"]["provider"] == "ollama"
        assert entity.extra_metadata["llm_refinement"]["model"] == "test-model"
        assert entity.extra_metadata["llm_refinement"]["prompt_version"] == "test-prompt-v1"
    finally:
        db_session.execute(delete(EntityMention).where(EntityMention.document_id == document.id))
        db_session.execute(delete(ProcessingJob).where(ProcessingJob.document_id == document.id))
        db_session.execute(delete(Entity).where(Entity.id == entity.id))
        db_session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db_session.delete(document)
        db_session.commit()


def test_refinement_worker_records_entity_failures_and_continues(
    db_session,
    document,
    document_chunk,
    monkeypatch,
) -> None:
    entities = [
        Entity(entity_type="ISP_BLOCK", name="IFE", normalized_name="IFE", confidence=0.55, extra_metadata={}),
        Entity(entity_type="ISP_BLOCK", name="CSID", normalized_name="CSID", confidence=0.55, extra_metadata={}),
    ]
    db_session.add_all(entities)
    db_session.flush()
    for entity in entities:
        db_session.add(
            EntityMention(
                entity_id=entity.id,
                document_id=document.id,
                chunk_id=document_chunk.id,
                page_number=1,
                snippet=f"{entity.name} appears in the ISP pipeline.",
                confidence=0.9,
                extra_metadata={},
            )
        )
    job = ProcessingJob(
        document_id=document.id,
        status="queued",
        extra_metadata={"job_type": "llm_refinement"},
    )
    db_session.add(job)
    db_session.commit()

    class FakeKnowledgeRefinementService:
        provider = "ollama"
        model = "test-model"
        PROMPT_VERSION = "test-prompt-v1"

        def refine_entity(self, *, name, entity_type, snippets):  # noqa: ANN001, ARG002
            if name == "CSID":
                raise RuntimeError("LLM unavailable")
            return KnowledgeCardRefinement(
                accepted=True,
                description="Refined IFE description.",
                summary="Refined IFE summary.",
                confidence=0.9,
            )

    monkeypatch.setattr(refinement_worker, "KnowledgeRefinementService", FakeKnowledgeRefinementService)

    try:
        run_llm_refinement_job(job.id)

        db_session.refresh(job)
        for entity in entities:
            db_session.refresh(entity)

        assert job.status == "partially_processed"
        assert job.extra_metadata["processed_entities"] == 1
        assert job.extra_metadata["failed_entities"] == 1
        assert job.extra_metadata["entity_failures"]
        assert entities[1].description is None
    finally:
        db_session.execute(delete(EntityMention).where(EntityMention.document_id == document.id))
        db_session.execute(delete(ProcessingJob).where(ProcessingJob.document_id == document.id))
        db_session.execute(delete(Entity).where(Entity.id.in_([entity.id for entity in entities])))
        db_session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db_session.delete(document)
        db_session.commit()
