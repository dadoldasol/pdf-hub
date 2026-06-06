from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentPage
from app.models.entity import Entity, EntityMention
from app.models.graph import KnowledgeNode
from app.models.job import ProcessingJob
from app.services.embedding_service import EmbeddingService
from app.services.entity_extraction_service import EntityCandidate, EntityExtractionService
from app.services.entity_validation_service import EntityValidationService
from app.services.pdf_processing_service import PdfProcessingService


class JobCanceled(Exception):
    """Raised when a user requests cancellation for an ingestion job."""


def run_ingestion_job(job_id: UUID) -> None:
    """Run the MVP PDF extraction pipeline for one processing job."""
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return

        document = db.get(Document, job.document_id)
        if document is None:
            job.status = "failed"
            job.error_message = "Document not found."
            job.finished_at = datetime.now(UTC)
            db.commit()
            return

        if job.status == "canceled" or (job.extra_metadata or {}).get("cancel_requested"):
            _mark_job_canceled(job, document)
            db.commit()
            return

        _start_job(job)
        document.status = "processing"
        db.commit()
        _raise_if_canceled(db, job)

        pdf_service = PdfProcessingService()
        pdf_path = Path(document.storage_path)
        page_count = pdf_service.get_page_count(pdf_path)

        db.execute(delete(EntityMention).where(EntityMention.document_id == document.id))
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
        document.page_count = page_count
        _set_job_progress(job, "extracting_pdf", total_pages=page_count)
        db.commit()
        _raise_if_canceled(db, job)

        chunk_count = _extract_pages_and_chunks(db, job, document, pdf_service, pdf_path)
        _embed_chunks(db, job, document.id, chunk_count)
        entity_mentions = _extract_entities(db, job, document.id, chunk_count)

        _set_job_progress(
            job,
            "completed",
            stage="completed",
            processed_pages=page_count,
            processed_chunks=chunk_count,
            total_chunks=chunk_count,
            entity_mentions=entity_mentions,
        )
        job.finished_at = datetime.now(UTC)
        document.status = "processed"
        db.commit()
    except JobCanceled:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job is not None:
            document = db.get(Document, job.document_id)
            _mark_job_canceled(job, document)
            db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job is not None:
            document = db.get(Document, job.document_id)
            job.status = "failed"
            job.error_message = _format_error_message(exc)
            job.finished_at = datetime.now(UTC)
            metadata = dict(job.extra_metadata or {})
            metadata["stage"] = "failed"
            metadata["error_type"] = type(exc).__name__
            job.extra_metadata = metadata
            if document is not None:
                document.status = "failed"
            db.commit()
        raise
    finally:
        db.close()


def _start_job(job: ProcessingJob) -> None:
    job.status = "extracting_pdf"
    job.error_message = None
    job.started_at = datetime.now(UTC)
    job.finished_at = None
    metadata = dict(job.extra_metadata or {})
    metadata.update(
        {
        "stage": "extracting_pdf",
        "total_pages": None,
        "processed_pages": 0,
        "total_chunks": 0,
        "processed_chunks": 0,
        "entity_mentions": 0,
        "entity_candidates": 0,
        "entities_accepted": 0,
        "entities_rejected": 0,
        }
    )
    job.extra_metadata = metadata


def _extract_pages_and_chunks(
    db: Session,
    job: ProcessingJob,
    document: Document,
    pdf_service: PdfProcessingService,
    pdf_path: Path,
) -> int:
    chunk_index = 0

    def mark_page_started(page_number: int) -> None:
        _set_job_progress(
            job,
            "extracting_pdf",
            current_page=page_number,
            current_page_status="extracting_text",
        )
        db.commit()

    for page in pdf_service.iter_pages(pdf_path, before_page=mark_page_started):
        _raise_if_canceled(db, job)
        _set_job_progress(
            job,
            "extracting_pdf",
            current_page=page.page_number,
            current_page_status="saving_text",
            last_page_seconds=round(page.extraction_seconds, 3),
        )
        page_row = DocumentPage(
            document_id=document.id,
            page_number=page.page_number,
            text=page.text,
            needs_ocr=page.needs_ocr,
            extraction_status=page.extraction_status,
            extraction_error=page.extraction_error,
            extraction_seconds=page.extraction_seconds,
            extra_metadata={},
        )
        db.add(page_row)
        db.flush()

        _set_job_progress(job, "chunking", stage="chunking", current_page=page.page_number)
        chunk_started_at = perf_counter()
        for chunk_text in pdf_service.chunk_text(page.text):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_id=page_row.id,
                    chunk_index=chunk_index,
                    page_number=page.page_number,
                    text=chunk_text,
                    embedding=None,
                    extra_metadata={},
                )
            )
            chunk_index += 1

        _set_job_progress(
            job,
            "chunking",
            processed_pages=page.page_number,
            total_chunks=chunk_index,
            current_page_status="chunked",
            last_chunk_seconds=round(perf_counter() - chunk_started_at, 3),
        )
        db.commit()
        _raise_if_canceled(db, job)

    db.commit()
    _raise_if_canceled(db, job)
    return chunk_index


def _embed_chunks(db: Session, job: ProcessingJob, document_id: UUID, chunk_count: int) -> None:
    _raise_if_canceled(db, job)
    _set_job_progress(
        job,
        "embedding",
        stage="embedding",
        processed_chunks=0,
        total_chunks=chunk_count,
    )
    db.commit()

    if not settings.enable_embeddings_on_upload:
        _set_job_progress(
            job,
            "embedding",
            processed_chunks=chunk_count,
            embedding_skipped=True,
        )
        db.commit()
        _raise_if_canceled(db, job)
        return

    embedding_service = EmbeddingService()
    processed_chunks = 0
    for chunk_batch in _iter_chunk_batches(db, document_id, settings.ingestion_batch_chunks):
        _raise_if_canceled(db, job)
        for chunk_row in chunk_batch:
            embedding = embedding_service.embed_text(chunk_row.text)
            chunk_row.embedding = embedding if embedding_service.has_signal(embedding) else None

        processed_chunks += len(chunk_batch)
        _set_job_progress(job, "embedding", processed_chunks=processed_chunks)
        db.commit()
        _raise_if_canceled(db, job)


def _extract_entities(db: Session, job: ProcessingJob, document_id: UUID, chunk_count: int) -> int:
    _raise_if_canceled(db, job)
    _set_job_progress(
        job,
        "extracting_knowledge",
        stage="extracting_knowledge",
        processed_chunks=0,
        total_chunks=chunk_count,
        entity_mentions=0,
    )
    db.commit()

    extraction_service = EntityExtractionService()
    validation_service = EntityValidationService()
    processed_chunks = 0
    entity_mentions = 0
    entity_candidates = 0
    entities_accepted = 0
    entities_rejected = 0
    validation_errors: list[str] = []
    for chunk_batch in _iter_chunk_batches(db, document_id, settings.ingestion_batch_chunks):
        _raise_if_canceled(db, job)
        for chunk_row in chunk_batch:
            candidates = extraction_service.extract(chunk_row.text)
            entity_candidates += len(candidates)
            validation_result = validation_service.validate_candidates(candidates, chunk_row.text)
            entities_accepted += len(validation_result.accepted_candidates)
            entities_rejected += validation_result.rejected_count
            if validation_result.error_message:
                validation_errors.append(validation_result.error_message)

            for candidate in validation_result.accepted_candidates:
                entity = _get_or_create_entity(db, candidate)
                _get_or_create_knowledge_node(db, entity)
                db.add(
                    EntityMention(
                        entity_id=entity.id,
                        document_id=document_id,
                        chunk_id=chunk_row.id,
                        page_number=chunk_row.page_number,
                        snippet=candidate.snippet,
                        confidence=candidate.confidence,
                        extra_metadata={
                            "source": candidate.source,
                            "validation_source": candidate.validation_source,
                        },
                    )
                )
                entity_mentions += 1

        processed_chunks += len(chunk_batch)
        _set_job_progress(
            job,
            "extracting_knowledge",
            processed_chunks=processed_chunks,
            entity_mentions=entity_mentions,
            entity_candidates=entity_candidates,
            entities_accepted=entities_accepted,
            entities_rejected=entities_rejected,
            entity_validation_errors=validation_errors[-3:],
        )
        db.commit()
        _raise_if_canceled(db, job)

    return entity_mentions


def _set_job_progress(job: ProcessingJob, status: str, **metadata_updates: object) -> None:
    metadata = dict(job.extra_metadata or {})
    metadata.update(metadata_updates)
    metadata.setdefault("stage", status)
    job.status = status
    job.extra_metadata = metadata


def _raise_if_canceled(db: Session, job: ProcessingJob) -> None:
    db.refresh(job)
    if (job.extra_metadata or {}).get("cancel_requested"):
        raise JobCanceled


def _mark_job_canceled(job: ProcessingJob, document: Document | None) -> None:
    metadata = dict(job.extra_metadata or {})
    metadata["stage"] = "canceled"
    metadata["cancel_requested"] = True
    job.status = "canceled"
    job.error_message = None
    job.finished_at = datetime.now(UTC)
    job.extra_metadata = metadata
    if document is not None:
        document.status = "canceled"


def _format_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return f"{type(exc).__name__}: {message}"
    return type(exc).__name__


def _iter_chunk_batches(db: Session, document_id: UUID, batch_size: int) -> Iterator[list[DocumentChunk]]:
    last_index = -1
    while True:
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.chunk_index > last_index,
            )
            .order_by(DocumentChunk.chunk_index)
            .limit(batch_size)
        )
        chunk_batch = list(db.scalars(stmt))
        if not chunk_batch:
            break

        yield chunk_batch
        last_index = chunk_batch[-1].chunk_index


def _get_or_create_entity(db: Session, candidate: EntityCandidate) -> Entity:
    entity = db.scalar(
        select(Entity).where(
            Entity.normalized_name == candidate.normalized_name,
            Entity.entity_type == candidate.entity_type,
        )
    )
    if entity is not None:
        if candidate.description and not entity.description:
            entity.description = candidate.description
        if entity.confidence is None or candidate.confidence > entity.confidence:
            entity.confidence = candidate.confidence
        metadata = dict(entity.extra_metadata or {})
        aliases = set(metadata.get("aliases") or [])
        aliases.update(candidate.aliases)
        metadata["aliases"] = sorted(aliases)
        metadata["validation_source"] = candidate.validation_source
        entity.extra_metadata = metadata
        return entity

    entity = Entity(
        entity_type=candidate.entity_type,
        name=candidate.name,
        normalized_name=candidate.normalized_name,
        description=candidate.description,
        confidence=candidate.confidence,
        extra_metadata={
            "source": candidate.source,
            "validation_source": candidate.validation_source,
            "aliases": list(candidate.aliases),
        },
    )
    db.add(entity)
    db.flush()
    return entity


def _get_or_create_knowledge_node(db: Session, entity: Entity) -> KnowledgeNode:
    node = db.scalar(
        select(KnowledgeNode).where(
            KnowledgeNode.entity_id == entity.id,
            KnowledgeNode.node_type == entity.entity_type,
        )
    )
    if node is not None:
        return node

    node = KnowledgeNode(
        entity_id=entity.id,
        node_type=entity.entity_type,
        name=entity.name,
        normalized_name=entity.normalized_name,
        description=entity.description,
        extra_metadata={},
    )
    db.add(node)
    db.flush()
    return node
