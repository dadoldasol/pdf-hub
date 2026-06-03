from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    status: str
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
