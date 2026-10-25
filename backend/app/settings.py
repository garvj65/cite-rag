"""Typed configuration; importing this module does not contact external services."""

from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# All supported providers request this dimension so one migration serves both.
EMBEDDING_DIMENSIONS = 1536
PROXY_RESPONSE_MARGIN_SECONDS = 5
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
    llm_provider: Literal["gemini", "openai", "fake"] = "gemini"
    gemini_chat_model: str = "gemini-3.8-flash"
    openai_chat_model: str = ""
    fake_llm_response: str = Field(
        default='{"answer":"","citations":[],"supported":false}', repr=False
    )
    answer_min_vector_score: float = Field(default=0.35, ge=-1, le=1)
    answer_min_keyword_score: float = Field(default=0.05, ge=0)
    answer_min_hybrid_score: float = Field(default=0.02, ge=0)
    answer_context_characters: int = Field(default=24000, ge=1024, le=100000)
    answer_max_characters: int = Field(default=12000, ge=1, le=50000)
    answer_max_citations: int = Field(default=8, ge=1, le=50)
    answer_max_quote_characters: int = Field(default=2000, ge=1, le=10000)
    model_max_output_characters: int = Field(default=50000, ge=1, le=200000)
    chat_max_completion_tokens: int = Field(default=4096, ge=256, le=16384)
    chunk_size_words: int = Field(default=400, ge=1, le=2000)
    chunk_overlap_words: int = Field(default=80, ge=0)
    embedding_batch_size: int = Field(default=16, ge=1, le=100)
    provider_timeout_seconds: float = Field(default=30, gt=0, le=120)
    provider_max_attempts: int = Field(default=3, ge=1, le=5)
    provider_backoff_seconds: float = Field(default=1, ge=0, le=30)
    provider_max_backoff_seconds: float = Field(default=8, ge=0, le=60)
    request_deadline_seconds: float = Field(default=90, gt=0, le=1800)
    proxy_timeout_seconds: int = Field(default=100, ge=1, le=3600)
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
        if (
            self.request_deadline_seconds + PROXY_RESPONSE_MARGIN_SECONDS
            > self.proxy_timeout_seconds
        ):
            raise ValueError("proxy timeout must exceed the API deadline by at least five seconds")
        return self
