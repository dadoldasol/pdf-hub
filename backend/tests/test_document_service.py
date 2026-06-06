import asyncio
import uuid
from pathlib import Path

from app.models.chunk import DocumentChunk
from app.models.entity import Entity, EntityMention
from app.models.graph import KnowledgeNode
from app.models.job import ProcessingJob
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService


class FakeUploadFile:
    def __init__(
        self,
        content: bytes,
        filename: str = "sample.pdf",
        content_type: str = "application/pdf",
    ) -> None:
        self._content = content
        self._offset = 0
        self.filename = filename
        self.content_type = content_type

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._content):
            return b""
        if size < 0:
            size = len(self._content) - self._offset
        chunk = self._content[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _document_service(db_session, tmp_path: Path) -> DocumentService:
    service = DocumentService(db_session)
    service.storage = StorageService(tmp_path)
    return service


def test_create_document_from_upload_deduplicates_by_file_hash(db_session, tmp_path: Path) -> None:
    service = _document_service(db_session, tmp_path)
    content = f"%PDF same content {uuid.uuid4()}".encode()
    document_id = None

    try:
        first_document, first_job, first_duplicate = asyncio.run(
            service.create_document_from_upload(FakeUploadFile(content))
        )
        document_id = first_document.id
        second_document, second_job, second_duplicate = asyncio.run(
            service.create_document_from_upload(FakeUploadFile(content, filename="copy.pdf"))
        )

        assert first_duplicate is False
        assert first_job is not None
        assert second_duplicate is True
        assert second_job is None
        assert second_document.id == first_document.id
        assert first_document.file_hash
        assert len(list(tmp_path.iterdir())) == 1
    finally:
        if document_id is not None:
            service.delete_document(document_id)


def test_delete_document_removes_document_scoped_rows_and_file(db_session, document, tmp_path: Path) -> None:
    pdf_path = tmp_path / "delete-me.pdf"
    pdf_path.write_bytes(b"%PDF delete me")
    document.storage_path = str(pdf_path)
    document.file_hash = uuid.uuid4().hex + uuid.uuid4().hex

    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=10,
        page_number=3,
        text="IFE appears.",
        extra_metadata={},
    )
    entity = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        confidence=0.95,
        extra_metadata={},
    )
    job = ProcessingJob(document_id=document.id, status="completed", extra_metadata={})
    db_session.add_all([chunk, entity, job])
    db_session.flush()

    mention = EntityMention(
        entity_id=entity.id,
        document_id=document.id,
        chunk_id=chunk.id,
        page_number=3,
        snippet="IFE appears.",
        confidence=0.95,
        extra_metadata={},
    )
    node = KnowledgeNode(
        entity_id=entity.id,
        node_type=entity.entity_type,
        name=entity.name,
        normalized_name=entity.normalized_name,
        extra_metadata={},
    )
    db_session.add_all([mention, node])
    db_session.commit()

    document_id = document.id
    chunk_id = chunk.id
    mention_id = mention.id
    entity_id = entity.id
    node_id = node.id
    job_id = job.id
    service = _document_service(db_session, tmp_path)

    assert service.delete_document(document_id) is True

    assert db_session.get(type(document), document_id) is None
    assert db_session.get(DocumentChunk, chunk_id) is None
    assert db_session.get(EntityMention, mention_id) is None
    assert db_session.get(Entity, entity_id) is None
    assert db_session.get(KnowledgeNode, node_id) is None
    assert db_session.get(ProcessingJob, job_id) is None
    assert not pdf_path.exists()


def test_delete_document_removes_preexisting_orphan_entities(db_session, document, tmp_path: Path) -> None:
    pdf_path = tmp_path / "delete-orphan.pdf"
    pdf_path.write_bytes(b"%PDF delete orphan")
    document.storage_path = str(pdf_path)
    document.file_hash = uuid.uuid4().hex + uuid.uuid4().hex
    orphan = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        confidence=0.95,
        extra_metadata={},
    )
    db_session.add(orphan)
    db_session.flush()
    orphan_node = KnowledgeNode(
        entity_id=orphan.id,
        node_type=orphan.entity_type,
        name=orphan.name,
        normalized_name=orphan.normalized_name,
        extra_metadata={},
    )
    db_session.add(orphan_node)
    db_session.commit()
    orphan_id = orphan.id
    orphan_node_id = orphan_node.id
    service = _document_service(db_session, tmp_path)

    assert service.delete_document(document.id) is True

    assert db_session.get(Entity, orphan_id) is None
    assert db_session.get(KnowledgeNode, orphan_node_id) is None
