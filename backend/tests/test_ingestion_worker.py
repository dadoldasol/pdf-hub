from sqlalchemy import delete

from app.models.job import ProcessingJob
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
