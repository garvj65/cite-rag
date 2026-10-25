"""Keep retrieval algorithms independent from HTTP and concrete database sessions."""

from collections.abc import Sequence
from typing import Protocol

from app.retrieval.models import SearchHit


class Retriever(Protocol):
    """Expose one search contract for vector, keyword, and hybrid retrieval."""

    def search(self, query: str, k: int) -> list[SearchHit]:
        """Return ranked passages, restricted to the configured indexing profile."""
        ...


class SearchRepository(Protocol):
    """Expose PostgreSQL search operations needed by retrieval strategies."""

    def has_profile(self, profile: str) -> bool:
        """Report whether this exact chunking/model configuration has stored passages."""
        ...

    def vector_search(self, profile: str, vector: Sequence[float], k: int) -> list[SearchHit]:
        """Rank stored chunks by cosine similarity with deterministic ties."""
        ...

    def keyword_search(self, profile: str, query: str, k: int) -> list[SearchHit]:
        """Rank matching chunks using PostgreSQL full-text search."""
        ...
