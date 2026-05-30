from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentPage
from app.models.job import ProcessingJob
from app.services.storage_service import StorageService


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage = StorageService()

    async def create_document_from_upload(self, file: UploadFile) -> tuple[Document, ProcessingJob]:
        storage_path, size = await self.storage.save_upload(file)
        title = Path(file.filename or storage_path.name).stem

        document = Document(
            title=title,
            original_filename=file.filename or storage_path.name,
            storage_path=str(storage_path),
            content_type=file.content_type,
            file_size_bytes=size,
            status="uploaded",
            extra_metadata={},
        )
        self.db.add(document)
        self.db.flush()

        job = ProcessingJob(document_id=document.id, status="queued", extra_metadata={})
        self.db.add(job)
        self.db.commit()
        self.db.refresh(document)
        self.db.refresh(job)

        return document, job

    def list_documents(self) -> list[Document]:
        return list(self.db.scalars(select(Document).order_by(Document.created_at.desc())))

    def get_document(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def get_page(self, document_id: UUID, page_number: int) -> DocumentPage | None:
        stmt = select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number,
        )
        return self.db.scalar(stmt)

    def get_job(self, job_id: UUID) -> ProcessingJob | None:
        return self.db.get(ProcessingJob, job_id)

