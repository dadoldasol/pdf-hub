from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    job_id: UUID
    status: str


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_filename: str
    status: str
    page_count: int | None
    created_at: datetime


class DocumentDetail(DocumentListItem):
    storage_path: str
    content_type: str | None
    file_size_bytes: int
    summary: str | None


class PageDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    page_number: int
    text: str
    needs_ocr: bool

