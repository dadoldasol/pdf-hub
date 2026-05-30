from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job import JobDetail
from app.services.document_service import DocumentService

router = APIRouter()


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> JobDetail:
    job = DocumentService(db).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

