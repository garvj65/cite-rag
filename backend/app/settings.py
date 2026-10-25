"""Typed configuration; importing this module does not contact external services."""

from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# All supported providers request this dimension so one migration serves both.
EMBEDDING_DIMENSIONS = 1536
RetrievalStrategy = Literal["vector", "keyword", "hybrid"]


class Settings(BaseSettings):
    """Validate application settings supplied through environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://citerag:local-development-only@localhost:5432/citerag"
    )
    enable_real_providers: bool = False
    embedding_provider: Literal["gemini", "openai", "fake"] = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    gemini_embedding_model: str = "gemini-embedding-2"
    openai_embedding_model: str = "text-embedding-3-small"
    chunk_size_words: int = Field(default=400, ge=1, le=2000)
    chunk_overlap_words: int = Field(default=80, ge=0)
    embedding_batch_size: int = Field(default=16, ge=1, le=100)
    provider_timeout_seconds: float = Field(default=30, gt=0, le=120)
    provider_max_attempts: int = Field(default=3, ge=1, le=5)
    provider_backoff_seconds: float = Field(default=1, ge=0, le=30)
    provider_max_backoff_seconds: float = Field(default=8, ge=0, le=60)
    max_pdf_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    max_pdf_pages: int = Field(default=500, ge=1)
    search_strategy: RetrievalStrategy = "hybrid"
    search_k: int = Field(default=5, ge=1)
    search_max_k: int = Field(default=50, ge=1, le=100)
    max_query_characters: int = Field(default=2000, ge=1, le=20000)
    hybrid_candidate_k: int = Field(default=20, ge=1, le=1000)
    rrf_constant: int = Field(default=60, ge=0, le=10000)

    @model_validator(mode="after")
    def validate_overlap(self) -> Self:
        """Require progress in the sliding chunk window."""
        if self.chunk_overlap_words >= self.chunk_size_words:
            raise ValueError("chunk_overlap_words must be smaller than chunk_size_words")
        if self.search_k > self.search_max_k:
            raise ValueError("search_k must not exceed search_max_k")
        return self
