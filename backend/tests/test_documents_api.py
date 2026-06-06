from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.document import Document
from app.models.job import ProcessingJob
from app.services.document_service import DocumentService


def test_upload_creates_queued_job_without_running_ingestion(
    db_session,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "pdf_storage_dir", tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("queued.pdf", b"%PDF queued", "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    document_id = UUID(payload["document_id"])
    job_id = UUID(payload["job_id"])

    try:
        document = db_session.get(Document, document_id)
        job = db_session.get(ProcessingJob, job_id)

        assert payload["status"] == "queued"
        assert document is not None
        assert document.status == "uploaded"
        assert job is not None
        assert job.status == "queued"
    finally:
        DocumentService(db_session).delete_document(document_id)
