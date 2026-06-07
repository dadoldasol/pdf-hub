from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentPage
from app.models.entity import Entity, EntityMention
from app.models.graph import KnowledgeEdge, KnowledgeNode
from app.models.job import ProcessingJob
from app.services.storage_service import StorageService


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage = StorageService()

    async def create_document_from_upload(self, file: UploadFile) -> tuple[Document, ProcessingJob | None, bool]:
        storage_path, size, file_hash = await self.storage.save_upload(file)
        existing_document = self.get_document_by_hash(file_hash)
        if existing_document is not None:
            self.storage.delete_file(storage_path)
            return existing_document, None, True

        title = Path(file.filename or storage_path.name).stem

        document = Document(
            title=title,
            original_filename=file.filename or storage_path.name,
            storage_path=str(storage_path),
            content_type=file.content_type,
            file_size_bytes=size,
            file_hash=file_hash,
            status="uploaded",
            extra_metadata={},
        )
        self.db.add(document)
        self.db.flush()

        job = ProcessingJob(document_id=document.id, status="queued", extra_metadata={"job_type": "ingestion"})
        self.db.add(job)
        self.db.commit()
        self.db.refresh(document)
        self.db.refresh(job)

        return document, job, False

    def list_documents(self) -> list[Document]:
        return list(self.db.scalars(select(Document).order_by(Document.created_at.desc())))

    def get_document(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def get_document_by_hash(self, file_hash: str) -> Document | None:
        return self.db.scalar(select(Document).where(Document.file_hash == file_hash))

    def get_page(self, document_id: UUID, page_number: int) -> DocumentPage | None:
        stmt = select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number,
        )
        return self.db.scalar(stmt)

    def get_job(self, job_id: UUID) -> ProcessingJob | None:
        return self.db.get(ProcessingJob, job_id)

    def delete_document(self, document_id: UUID) -> bool:
        document = self.get_document(document_id)
        if document is None:
            return False

        entity_ids = set(
            self.db.scalars(select(EntityMention.entity_id).where(EntityMention.document_id == document_id))
        )
        chunk_ids = set(self.db.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id == document_id)))
        node_ids = set(
            self.db.scalars(select(KnowledgeNode.id).where(KnowledgeNode.entity_id.in_(entity_ids)))
        )

        for job in self.db.scalars(select(ProcessingJob).where(ProcessingJob.document_id == document_id)):
            metadata = dict(job.extra_metadata or {})
            metadata["cancel_requested"] = True
            metadata["cancel_reason"] = "document_deleted"
            job.extra_metadata = metadata

        if chunk_ids:
            self.db.execute(delete(KnowledgeEdge).where(KnowledgeEdge.source_chunk_id.in_(chunk_ids)))

        self.db.execute(delete(EntityMention).where(EntityMention.document_id == document_id))
        self.db.execute(delete(ProcessingJob).where(ProcessingJob.document_id == document_id))
        self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        self.db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        self.db.delete(document)
        self.db.flush()

        self._delete_orphan_entities(entity_ids)
        self._delete_all_orphan_entities()
        self._delete_orphan_nodes(node_ids)
        self.db.commit()
        self.storage.delete_file(Path(document.storage_path))
        return True

    def _delete_orphan_entities(self, entity_ids: set[UUID]) -> None:
        for entity_id in entity_ids:
            mention_count = self.db.scalar(
                select(func.count(EntityMention.id)).where(EntityMention.entity_id == entity_id)
            )
            if mention_count:
                continue

            nodes = list(self.db.scalars(select(KnowledgeNode).where(KnowledgeNode.entity_id == entity_id)))
            node_ids = [node.id for node in nodes]
            if node_ids:
                self.db.execute(
                    delete(KnowledgeEdge).where(
                        (KnowledgeEdge.source_node_id.in_(node_ids))
                        | (KnowledgeEdge.target_node_id.in_(node_ids))
                    )
                )
                self.db.execute(delete(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids)))

            self.db.execute(delete(Entity).where(Entity.id == entity_id))

    def _delete_all_orphan_entities(self) -> None:
        orphan_entity_ids = set(
            self.db.scalars(
                select(Entity.id)
                .outerjoin(EntityMention, EntityMention.entity_id == Entity.id)
                .group_by(Entity.id)
                .having(func.count(EntityMention.id) == 0)
            )
        )
        self._delete_orphan_entities(orphan_entity_ids)

    def _delete_orphan_nodes(self, node_ids: set[UUID]) -> None:
        for node_id in node_ids:
            edge_count = self.db.scalar(
                select(func.count(KnowledgeEdge.id)).where(
                    (KnowledgeEdge.source_node_id == node_id) | (KnowledgeEdge.target_node_id == node_id)
                )
            )
            if edge_count:
                continue
            node = self.db.get(KnowledgeNode, node_id)
            if node is not None and node.entity_id is None:
                self.db.delete(node)
