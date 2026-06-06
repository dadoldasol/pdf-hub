from types import SimpleNamespace

from sqlalchemy import delete

from app.models.chunk import DocumentChunk
from app.models.document import DocumentPage
from app.models.job import ProcessingJob
from app.workers import ingestion_worker
from app.workers.ingestion_worker import run_ingestion_job
from app.workers.worker_main import claim_next_queued_job


def test_ingestion_job_marks_document_failed_for_invalid_pdf_path(db_session, document) -> None:
    document.storage_path = "missing-file.pdf"
    job = ProcessingJob(document_id=document.id, status="queued", extra_metadata={})
    db_session.add(job)
    db_session.commit()

    try:
        try:
            run_ingestion_job(job.id)
        except Exception:
            pass

        db_session.refresh(document)
        db_session.refresh(job)

        assert document.status == "failed"
        assert job.status == "failed"
        assert job.error_message
    finally:
        db_session.execute(delete(ProcessingJob).where(ProcessingJob.id == job.id))
        db_session.delete(document)
        db_session.commit()


def test_worker_claims_oldest_queued_job(db_session, document) -> None:
    first_job = ProcessingJob(document_id=document.id, status="queued", extra_metadata={})
    second_job = ProcessingJob(document_id=document.id, status="queued", extra_metadata={})
    db_session.add_all([first_job, second_job])
    db_session.commit()

    try:
        claimed_job_id = claim_next_queued_job("test-worker")

        db_session.refresh(first_job)
        db_session.refresh(second_job)

        assert claimed_job_id == first_job.id
        assert first_job.status == "claimed"
        assert first_job.extra_metadata["worker_id"] == "test-worker"
        assert first_job.extra_metadata["stage"] == "claimed"
        assert second_job.status == "queued"
    finally:
        db_session.execute(delete(ProcessingJob).where(ProcessingJob.id.in_([first_job.id, second_job.id])))
        db_session.delete(document)
        db_session.commit()


def test_ingestion_commits_each_page_before_later_extraction_failure(
    db_session,
    document,
    monkeypatch,
) -> None:
    class FakePdfProcessingService:
        def get_page_count(self, pdf_path):  # noqa: ANN001
            return 2

        def iter_pages(self, pdf_path, before_page=None):  # noqa: ANN001
            if before_page is not None:
                before_page(1)
            yield SimpleNamespace(
                page_number=1,
                text="IFE first page text.",
                needs_ocr=False,
                extraction_seconds=0.01,
                extraction_status="completed",
                extraction_error=None,
            )
            if before_page is not None:
                before_page(2)
            raise RuntimeError("second page extraction failed")

        def chunk_text(self, text):  # noqa: ANN001
            return [text]

    document.storage_path = "fake.pdf"
    document.status = "uploaded"
    job = ProcessingJob(document_id=document.id, status="queued", extra_metadata={})
    db_session.add(job)
    db_session.commit()
    monkeypatch.setattr(ingestion_worker, "PdfProcessingService", FakePdfProcessingService)

    try:
        try:
            run_ingestion_job(job.id)
        except RuntimeError:
            pass

        db_session.refresh(document)
        db_session.refresh(job)
        pages = list(db_session.query(DocumentPage).filter(DocumentPage.document_id == document.id))
        chunks = list(db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id))

        assert document.status == "failed"
        assert job.status == "failed"
        assert [page.page_number for page in pages] == [1]
        assert [chunk.page_number for chunk in chunks] == [1]
    finally:
        db_session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db_session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
        db_session.execute(delete(ProcessingJob).where(ProcessingJob.id == job.id))
        db_session.delete(document)
        db_session.commit()


def test_ingestion_marks_document_partially_processed_for_failed_pages(
    db_session,
    document,
    monkeypatch,
) -> None:
    class FakePdfProcessingService:
        def get_page_count(self, pdf_path):  # noqa: ANN001
            return 2

        def iter_pages(self, pdf_path, before_page=None):  # noqa: ANN001
            for page_number, status in [(1, "completed"), (2, "timeout")]:
                if before_page is not None:
                    before_page(page_number)
                yield SimpleNamespace(
                    page_number=page_number,
                    text="IFE first page text." if status == "completed" else "",
                    needs_ocr=status != "completed",
                    extraction_seconds=0.01,
                    extraction_status=status,
                    extraction_error=None if status == "completed" else "timeout",
                )

        def chunk_text(self, text):  # noqa: ANN001
            return [text] if text else []

    document.storage_path = "fake.pdf"
    document.status = "uploaded"
    job = ProcessingJob(document_id=document.id, status="queued", extra_metadata={})
    db_session.add(job)
    db_session.commit()
    monkeypatch.setattr(ingestion_worker, "PdfProcessingService", FakePdfProcessingService)

    try:
        run_ingestion_job(job.id)

        db_session.refresh(document)
        db_session.refresh(job)
        pages = list(
            db_session.query(DocumentPage)
            .filter(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
        )

        assert document.status == "partially_processed"
        assert job.status == "partially_processed"
        assert job.extra_metadata["failed_pages"] == 1
        assert job.extra_metadata["timeout_pages"] == 1
        assert [page.extraction_status for page in pages] == ["completed", "timeout"]
    finally:
        db_session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db_session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
        db_session.execute(delete(ProcessingJob).where(ProcessingJob.id == job.id))
        db_session.delete(document)
        db_session.commit()
