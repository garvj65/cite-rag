"""Provider contracts shared by ingestion, retrieval, and answer generation."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Embed input strings in order using an explicitly identified model."""

    @property
    def model_id(self) -> str:
        """Return the provider/model identity used in the indexing fingerprint."""
        ...

    @property
    def dimensions(self) -> int:
        """Return the number of components in each embedding."""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding for each input or raise a sanitized ProviderError."""
        ...


class LLMProvider(Protocol):
    """Generate model text without exposing a vendor SDK to application services."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return generated text; answer validation belongs to the application."""
        ...
