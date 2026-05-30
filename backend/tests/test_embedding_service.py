from app.services.embedding_service import EmbeddingService


def test_embedding_is_deterministic_and_normalized() -> None:
    service = EmbeddingService(dimensions=32)

    first = service.embed_text("IFE supports RDI path")
    second = service.embed_text("IFE supports RDI path")

    assert first == second
    assert service.has_signal(first) is True
    assert round(sum(value * value for value in first), 6) == 1.0


def test_empty_embedding_has_no_signal() -> None:
    service = EmbeddingService(dimensions=32)

    embedding = service.embed_text("...")

    assert service.has_signal(embedding) is False

