from app.models.entity import Entity, EntityMention
from app.schemas.search import SearchRequest
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService


def test_search_result_includes_related_entities(db_session, document, document_chunk) -> None:
    embedding_service = EmbeddingService()
    document_chunk.embedding = embedding_service.embed_text("IFE CSID RDI debug flow")

    ife = Entity(
        entity_type="ISP_BLOCK",
        name="IFE",
        normalized_name="IFE",
        confidence=0.95,
        extra_metadata={},
    )
    csid = Entity(
        entity_type="ISP_BLOCK",
        name="CSID",
        normalized_name="CSID",
        confidence=0.95,
        extra_metadata={},
    )
    db_session.add_all([ife, csid])
    db_session.flush()
    db_session.add_all(
        [
            EntityMention(
                entity_id=ife.id,
                document_id=document.id,
                chunk_id=document_chunk.id,
                page_number=1,
                snippet="IFE CSID RDI debug flow",
                confidence=0.95,
                extra_metadata={},
            ),
            EntityMention(
                entity_id=csid.id,
                document_id=document.id,
                chunk_id=document_chunk.id,
                page_number=1,
                snippet="IFE CSID RDI debug flow",
                confidence=0.95,
                extra_metadata={},
            ),
        ]
    )
    db_session.flush()

    response = SearchService(db_session).search(SearchRequest(query="IFE debug", top_k=1))

    assert len(response.results) == 1
    assert response.results[0].related_entities == ["CSID", "IFE"]
