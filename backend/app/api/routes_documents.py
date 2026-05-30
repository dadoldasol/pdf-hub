from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document import DocumentDetail, DocumentListItem, DocumentUploadResponse, PageDetail
from app.services.document_service import DocumentService
from app.workers.ingestion_worker import run_ingestion_job

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    service = DocumentService(db)
    document, job = await service.create_document_from_upload(file)
    background_tasks.add_task(run_ingestion_job, job.id)
    return DocumentUploadResponse(document_id=document.id, job_id=job.id, status=job.status)


@router.get("", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentListItem]:
    return DocumentService(db).list_documents()


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentDetail:
    document = DocumentService(db).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.get("/{document_id}/pages/{page_number}", response_model=PageDetail)
def get_document_page(
    document_id: UUID,
    page_number: int,
    db: Session = Depends(get_db),
) -> PageDetail:
    page = DocumentService(db).get_page(document_id, page_number)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page
