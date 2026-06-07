from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document import (
    DocumentDeleteResponse,
    DocumentDetail,
    DocumentListItem,
    DocumentRefineRequest,
    DocumentRefineResponse,
    DocumentUploadResponse,
    PageDetail,
)
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    response: Response,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    service = DocumentService(db)
    document, job, duplicate = await service.create_document_from_upload(file)
    if duplicate:
        response.status_code = status.HTTP_200_OK
        return DocumentUploadResponse(
            document_id=document.id,
            job_id=None,
            status="already_exists",
            duplicate=True,
            duplicate_of_document_id=document.id,
        )

    if job is None:
        raise HTTPException(status_code=500, detail="Processing job was not created.")

    return DocumentUploadResponse(document_id=document.id, job_id=job.id, status=job.status)


@router.get("", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentListItem]:
    return DocumentService(db).list_documents()


@router.post("/{document_id}/refine", response_model=DocumentRefineResponse, status_code=status.HTTP_202_ACCEPTED)
def refine_document(
    document_id: UUID,
    request: DocumentRefineRequest | None = None,
    db: Session = Depends(get_db),
) -> DocumentRefineResponse:
    job, duplicate = DocumentService(db).create_refinement_job(
        document_id,
        force=bool(request.force) if request is not None else False,
        source="manual_api",
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRefineResponse(
        document_id=document_id,
        job_id=job.id,
        status=job.status,
        duplicate=duplicate,
    )


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


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentDeleteResponse:
    deleted = DocumentService(db).delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentDeleteResponse(document_id=document_id, deleted=True)
