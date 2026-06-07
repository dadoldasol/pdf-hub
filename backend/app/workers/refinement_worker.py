from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select

from app.db.session import SessionLocal
from app.models.document import Document
from app.models.entity import Entity, EntityMention
from app.models.job import ProcessingJob
from app.services.knowledge_refinement_service import KnowledgeCardRefinement, KnowledgeRefinementService


class RefinementJobCanceled(Exception):
    """Raised when a user requests cancellation for a refinement job."""


@dataclass(frozen=True)
class RefinementTarget:
    entity_id: UUID
    name: str
    entity_type: str
    snippets: list[str]


def run_llm_refinement_job(job_id: UUID) -> None:
    service = KnowledgeRefinementService()
    target_ids = _start_refinement_job(job_id)
    processed_entities = 0
    failed_entities = 0
    failure_messages: list[str] = []

    try:
        for entity_id in target_ids:
            target = _load_target(job_id, entity_id, processed_entities, failed_entities, failure_messages)
            try:
                result = service.refine_entity(
                    name=target.name,
                    entity_type=target.entity_type,
                    snippets=target.snippets,
                )
                processed_entities += 1
                _save_refinement_result(
                    job_id,
                    target,
                    result,
                    service,
                    processed_entities,
                    failed_entities,
                    failure_messages,
                )
            except Exception as exc:
                failed_entities += 1
                failure_messages.append(f"{target.name}: {type(exc).__name__}: {exc}")
                _save_refinement_failure(
                    job_id,
                    target,
                    processed_entities,
                    failed_entities,
                    failure_messages,
                )

        _finish_refinement_job(job_id, processed_entities, failed_entities, failure_messages)
    except RefinementJobCanceled:
        _mark_refinement_canceled(job_id)


def _start_refinement_job(job_id: UUID) -> list[UUID]:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return []

        document = db.get(Document, job.document_id)
        if document is None:
            job.status = "failed"
            job.error_message = "Document not found."
            job.finished_at = datetime.now(UTC)
            db.commit()
            return []

        if _is_cancel_requested(job):
            raise RefinementJobCanceled

        target_ids = list(
            db.scalars(
                select(Entity.id)
                .join(EntityMention, EntityMention.entity_id == Entity.id)
                .where(EntityMention.document_id == job.document_id)
                .group_by(Entity.id)
                .order_by(Entity.normalized_name.asc())
            )
        )
        job.status = "refining_entities"
        job.error_message = None
        job.started_at = datetime.now(UTC)
        job.finished_at = None
        metadata = dict(job.extra_metadata or {})
        metadata.update(
            {
                "job_type": "llm_refinement",
                "stage": "refining_entities",
                "total_entities": len(target_ids),
                "processed_entities": 0,
                "failed_entities": 0,
                "entity_failures": [],
            }
        )
        job.extra_metadata = metadata
        db.commit()
        return target_ids
    finally:
        db.close()


def _load_target(
    job_id: UUID,
    entity_id: UUID,
    processed_entities: int,
    failed_entities: int,
    failure_messages: list[str],
) -> RefinementTarget:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None or _is_cancel_requested(job):
            raise RefinementJobCanceled

        entity = db.get(Entity, entity_id)
        if entity is None:
            raise RuntimeError(f"Entity not found: {entity_id}")

        snippets = list(
            db.scalars(
                select(EntityMention.snippet)
                .where(
                    EntityMention.document_id == job.document_id,
                    EntityMention.entity_id == entity_id,
                    EntityMention.snippet.is_not(None),
                )
                .order_by(desc(EntityMention.confidence).nullslast(), EntityMention.created_at.desc())
                .limit(12)
            )
        )
        metadata = dict(job.extra_metadata or {})
        metadata.update(
            {
                "stage": "refining_entities",
                "current_entity_id": str(entity_id),
                "current_entity_name": entity.name,
                "processed_entities": processed_entities,
                "failed_entities": failed_entities,
                "entity_failures": failure_messages[-5:],
            }
        )
        job.status = "refining_entities"
        job.extra_metadata = metadata
        db.commit()
        return RefinementTarget(
            entity_id=entity.id,
            name=entity.name,
            entity_type=entity.entity_type,
            snippets=[snippet for snippet in snippets if snippet],
        )
    finally:
        db.close()


def _save_refinement_result(
    job_id: UUID,
    target: RefinementTarget,
    result: KnowledgeCardRefinement,
    service: KnowledgeRefinementService,
    processed_entities: int,
    failed_entities: int,
    failure_messages: list[str],
) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None or _is_cancel_requested(job):
            raise RefinementJobCanceled

        entity = db.get(Entity, target.entity_id)
        if entity is not None:
            metadata = dict(entity.extra_metadata or {})
            metadata["knowledge_card"] = {
                "summary": result.summary,
                "features": result.features,
                "implementation_locations": result.implementation_locations,
                "debug_keywords": result.debug_keywords,
                "limitations": result.limitations,
            }
            metadata["llm_refinement"] = {
                "accepted": result.accepted,
                "confidence": result.confidence,
                "provider": service.provider,
                "model": service.model,
                "prompt_version": service.PROMPT_VERSION,
                "refined_at": datetime.now(UTC).isoformat(),
                "source_snippet_count": len(target.snippets),
            }
            entity.extra_metadata = metadata
            if result.accepted and result.description:
                entity.description = result.description
            if result.confidence is not None:
                entity.confidence = result.confidence

        metadata = dict(job.extra_metadata or {})
        metadata.update(
            {
                "stage": "refining_entities",
                "processed_entities": processed_entities,
                "failed_entities": failed_entities,
                "entity_failures": failure_messages[-5:],
            }
        )
        job.extra_metadata = metadata
        db.commit()
    finally:
        db.close()


def _save_refinement_failure(
    job_id: UUID,
    target: RefinementTarget,
    processed_entities: int,
    failed_entities: int,
    failure_messages: list[str],
) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None or _is_cancel_requested(job):
            raise RefinementJobCanceled

        metadata = dict(job.extra_metadata or {})
        metadata.update(
            {
                "stage": "refining_entities",
                "current_entity_id": str(target.entity_id),
                "current_entity_name": target.name,
                "processed_entities": processed_entities,
                "failed_entities": failed_entities,
                "entity_failures": failure_messages[-5:],
            }
        )
        job.extra_metadata = metadata
        db.commit()
    finally:
        db.close()


def _finish_refinement_job(
    job_id: UUID,
    processed_entities: int,
    failed_entities: int,
    failure_messages: list[str],
) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return
        if _is_cancel_requested(job):
            raise RefinementJobCanceled

        if failed_entities and processed_entities:
            final_status = "partially_processed"
        elif failed_entities:
            final_status = "failed"
        else:
            final_status = "completed"

        metadata = dict(job.extra_metadata or {})
        metadata.update(
            {
                "stage": final_status,
                "processed_entities": processed_entities,
                "failed_entities": failed_entities,
                "entity_failures": failure_messages[-5:],
            }
        )
        job.status = final_status
        job.error_message = "; ".join(failure_messages[-3:]) if final_status == "failed" else None
        job.finished_at = datetime.now(UTC)
        job.extra_metadata = metadata
        db.commit()
    finally:
        db.close()


def _mark_refinement_canceled(job_id: UUID) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return
        metadata = dict(job.extra_metadata or {})
        metadata["stage"] = "canceled"
        metadata["cancel_requested"] = True
        job.status = "canceled"
        job.error_message = None
        job.finished_at = datetime.now(UTC)
        job.extra_metadata = metadata
        db.commit()
    finally:
        db.close()


def _is_cancel_requested(job: ProcessingJob) -> bool:
    return bool((job.extra_metadata or {}).get("cancel_requested"))
