from uuid import UUID
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.schemas.job import JobDetail
from app.services.document_service import DocumentService

router = APIRouter()


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> JobDetail:
    job = DocumentService(db).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/{job_id}/cancel", response_model=JobDetail)
def cancel_job(job_id: UUID, db: Session = Depends(get_db)) -> JobDetail:
    job = DocumentService(db).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status in {"completed", "failed", "canceled"}:
        return job

    metadata = dict(job.extra_metadata or {})
    metadata["cancel_requested"] = True
    metadata["cancel_requested_at"] = datetime.now(UTC).isoformat()
    job.extra_metadata = metadata

    if job.status == "queued":
        job.status = "canceled"
        job.finished_at = datetime.now(UTC)
        document = db.get(Document, job.document_id)
        if document is not None:
            document.status = "canceled"

    db.commit()
    db.refresh(job)
    return job
