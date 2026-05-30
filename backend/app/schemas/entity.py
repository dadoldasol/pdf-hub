from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntityListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    name: str
    normalized_name: str
    description: str | None = None
    confidence: float | None = None


class EntityDetail(EntityListItem):
    pass


class SourcePage(BaseModel):
    document_id: UUID
    document_title: str
    page_number: int
    chunk_id: UUID | None = None
    snippet: str | None = None
    confidence: float | None = None


class KnowledgeCard(BaseModel):
    entity: EntityDetail
    summary: str | None = None
    features: list[str] = Field(default_factory=list)
    implementation_locations: list[str] = Field(default_factory=list)
    debug_keywords: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_pages: list[SourcePage] = Field(default_factory=list)
