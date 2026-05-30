from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    chunk_id: UUID | None = None
    document_id: UUID | None = None
    document_title: str | None = None
    page_number: int | None = None
    snippet: str
    score: float | None = None
    related_entities: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]

