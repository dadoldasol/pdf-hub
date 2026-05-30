from sqlalchemy import delete

from app.models.job import ProcessingJob
from app.workers.ingestion_worker import run_ingestion_job


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
