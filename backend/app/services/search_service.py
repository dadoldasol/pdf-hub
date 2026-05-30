from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.entity import Entity, EntityMention
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.embedding_service import EmbeddingService


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding_service = EmbeddingService()

    def search(self, request: SearchRequest) -> SearchResponse:
        query_embedding = self.embedding_service.embed_text(request.query)
        if not self.embedding_service.has_signal(query_embedding):
            return SearchResponse(query=request.query, results=[])

        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
        rows = (
            self.db.query(DocumentChunk, Document.title, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(DocumentChunk.embedding.is_not(None))
            .order_by(distance.asc())
            .limit(request.top_k)
            .all()
        )

        results = [
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=document_title,
                page_number=chunk.page_number,
                snippet=self._snippet(chunk.text),
                score=max(0.0, 1.0 - float(distance_value)),
                related_entities=self._related_entities(chunk.id),
            )
            for chunk, document_title, distance_value in rows
        ]
        return SearchResponse(query=request.query, results=results)

    def _related_entities(self, chunk_id) -> list[str]:
        rows = (
            self.db.query(Entity.name, Entity.normalized_name)
            .join(EntityMention, EntityMention.entity_id == Entity.id)
            .filter(EntityMention.chunk_id == chunk_id)
            .distinct()
            .order_by(Entity.normalized_name.asc())
            .all()
        )
        return [name for name, _ in rows]

    def _snippet(self, text: str, max_length: int = 500) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_length:
            return normalized
        return f"{normalized[: max_length - 3]}..."
