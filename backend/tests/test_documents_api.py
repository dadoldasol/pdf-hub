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


def test_refine_document_creates_refinement_job(db_session, document) -> None:
    client = TestClient(app)
    db_session.commit()

    try:
        response = client.post(f"/api/documents/{document.id}/refine")

        assert response.status_code == 202
        payload = response.json()
        job = db_session.get(ProcessingJob, UUID(payload["job_id"]))

        assert payload["document_id"] == str(document.id)
        assert payload["status"] == "queued"
        assert payload["duplicate"] is False
        assert job is not None
        assert job.extra_metadata["job_type"] == "llm_refinement"
        assert job.extra_metadata["source"] == "manual_api"
    finally:
        DocumentService(db_session).delete_document(document.id)


def test_refine_document_reuses_completed_job_unless_forced(db_session, document) -> None:
    client = TestClient(app)
    completed_job = ProcessingJob(
        document_id=document.id,
        status="completed",
        extra_metadata={"job_type": "llm_refinement"},
    )
    db_session.add(completed_job)
    db_session.commit()

    try:
        reuse_response = client.post(f"/api/documents/{document.id}/refine")
        force_response = client.post(f"/api/documents/{document.id}/refine", json={"force": True})

        assert reuse_response.status_code == 202
        assert force_response.status_code == 202
        assert UUID(reuse_response.json()["job_id"]) == completed_job.id
        assert reuse_response.json()["duplicate"] is True
        assert UUID(force_response.json()["job_id"]) != completed_job.id
        assert force_response.json()["duplicate"] is False
    finally:
        DocumentService(db_session).delete_document(document.id)


def test_list_documents_includes_latest_refinement_status(db_session, document) -> None:
    client = TestClient(app)
    older_job = ProcessingJob(
        document_id=document.id,
        status="completed",
        extra_metadata={
            "job_type": "llm_refinement",
            "stage": "completed",
            "processed_entities": 3,
            "total_entities": 3,
            "failed_entities": 0,
        },
    )
    db_session.add(older_job)
    db_session.commit()

    latest_job = ProcessingJob(
        document_id=document.id,
        status="refining_entities",
        extra_metadata={
            "job_type": "llm_refinement",
            "stage": "refining_entities",
            "processed_entities": 1,
            "total_entities": 4,
            "failed_entities": 1,
        },
    )
    db_session.add(latest_job)
    db_session.commit()

    try:
        response = client.get("/api/documents")

        assert response.status_code == 200
        payload = response.json()
        document_payload = next(item for item in payload if item["id"] == str(document.id))
        refinement_job = document_payload["refinement_job"]

        assert refinement_job["id"] == str(latest_job.id)
        assert refinement_job["status"] == "refining_entities"
        assert refinement_job["stage"] == "refining_entities"
        assert refinement_job["processed_entities"] == 1
        assert refinement_job["total_entities"] == 4
        assert refinement_job["failed_entities"] == 1
    finally:
        DocumentService(db_session).delete_document(document.id)
