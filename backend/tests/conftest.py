from collections.abc import Generator

import pytest

from app.db.session import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document


@pytest.fixture
def db_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def document(db_session) -> Document:
    document = Document(
        title="graph-test",
        original_filename="graph-test.pdf",
        storage_path="graph-test.pdf",
        content_type="application/pdf",
        file_size_bytes=100,
        status="processed",
        extra_metadata={},
    )
    db_session.add(document)
    db_session.flush()
    return document


@pytest.fixture
def document_chunk(db_session, document) -> DocumentChunk:
    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        page_number=1,
        text="IFE and CSID are related.",
        extra_metadata={},
    )
    db_session.add(chunk)
    db_session.flush()
    return chunk

