from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentPage
from app.models.entity import Entity, EntityMention
from app.models.graph import KnowledgeNode
from app.models.job import ProcessingJob
from app.services.embedding_service import EmbeddingService
from app.services.entity_extraction_service import EntityCandidate, EntityExtractionService
from app.services.pdf_processing_service import PdfProcessingService


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
            db.commit()
            return

        job.status = "extracting_pdf"
        job.error_message = None
        document.status = "processing"
        db.commit()

        extracted = PdfProcessingService().extract(Path(document.storage_path))

        db.execute(delete(EntityMention).where(EntityMention.document_id == document.id))
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
        db.flush()

        job.status = "chunking"
        document.page_count = extracted.page_count

        page_id_by_number: dict[int, UUID] = {}
        for page in extracted.pages:
            page_row = DocumentPage(
                document_id=document.id,
                page_number=page.page_number,
                text=page.text,
                needs_ocr=page.needs_ocr,
                extra_metadata={},
            )
            db.add(page_row)
            db.flush()
            page_id_by_number[page.page_number] = page_row.id

        job.status = "embedding"
        embedding_service = EmbeddingService()
        chunks: list[DocumentChunk] = []
        for chunk in extracted.chunks:
            embedding = embedding_service.embed_text(chunk.text)
            chunk_row = DocumentChunk(
                document_id=document.id,
                page_id=page_id_by_number.get(chunk.page_number),
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                embedding=embedding if embedding_service.has_signal(embedding) else None,
                extra_metadata={},
            )
            db.add(chunk_row)
            chunks.append(chunk_row)

        db.flush()

        job.status = "extracting_knowledge"
        extraction_service = EntityExtractionService()
        for chunk_row in chunks:
            for candidate in extraction_service.extract(chunk_row.text):
                entity = _get_or_create_entity(db, candidate)
                _get_or_create_knowledge_node(db, entity)
                db.add(
                    EntityMention(
                        entity_id=entity.id,
                        document_id=document.id,
                        chunk_id=chunk_row.id,
                        page_number=chunk_row.page_number,
                        snippet=candidate.snippet,
                        confidence=candidate.confidence,
                        extra_metadata={"source": candidate.source},
                    )
                )

        job.status = "completed"
        document.status = "processed"
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job is not None:
            document = db.get(Document, job.document_id)
            job.status = "failed"
            job.error_message = str(exc)
            if document is not None:
                document.status = "failed"
            db.commit()
        raise
    finally:
        db.close()


def _get_or_create_entity(db: Session, candidate: EntityCandidate) -> Entity:
    entity = db.scalar(
        select(Entity).where(
            Entity.normalized_name == candidate.normalized_name,
            Entity.entity_type == candidate.entity_type,
        )
    )
    if entity is not None:
        return entity

    entity = Entity(
        entity_type=candidate.entity_type,
        name=candidate.name,
        normalized_name=candidate.normalized_name,
        description=None,
        confidence=candidate.confidence,
        extra_metadata={"source": candidate.source},
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

