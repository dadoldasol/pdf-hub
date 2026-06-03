from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PDF Knowledge Hub"
    app_env: str = "local"
    debug: bool = True
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pdf_hub"
    pdf_storage_dir: Path = Path("./storage/pdfs")

    openai_api_key: str | None = None
    llm_model: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int = 1536
    ingestion_batch_pages: int = 5
    ingestion_batch_chunks: int = 50
    enable_embeddings_on_upload: bool = True
    pdf_text_extraction_mode: str = "blocks"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
