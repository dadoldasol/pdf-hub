from pathlib import Path
from uuid import UUID

from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentPage
from app.models.job import ProcessingJob
from app.services.embedding_service import EmbeddingService
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
        for chunk in extracted.chunks:
            embedding = embedding_service.embed_text(chunk.text)
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_id=page_id_by_number.get(chunk.page_number),
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    embedding=embedding if embedding_service.has_signal(embedding) else None,
                    extra_metadata={},
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
