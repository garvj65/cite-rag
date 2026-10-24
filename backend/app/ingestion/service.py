"""Coordinate extraction, chunking, embedding batches, and one atomic database write."""

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.db.repository import IngestionRepository
from app.errors import IngestionError, ProviderError
from app.ingestion.chunk import chunk_pages
from app.ingestion.extract import extract_pages
from app.ingestion.manifest import CorpusDocument
from app.providers.interfaces import EmbeddingProvider
from app.settings import EMBEDDING_DIMENSIONS, Settings


@dataclass(frozen=True)
class IngestionResult:
    """Describe one file without leaking extracted text or provider details."""

    filename: str
    status: Literal["indexed", "skipped", "failed"]
    reason: str
    doc_id: str | None = None
    pages: int = 0
    chunks: int = 0
    empty_pages: int = 0


def indexing_profile(settings: Settings, provider: EmbeddingProvider) -> str:
    """Fingerprint all current extraction, chunking, and embedding semantics."""
    config = {
        "pipeline": "pypdf-whitespace-page-words-v1",
        "chunk_size_words": settings.chunk_size_words,
        "chunk_overlap_words": settings.chunk_overlap_words,
        "model": provider.model_id,
        "dimensions": provider.dimensions,
    }
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def validate_vectors(vectors: Sequence[list[float]], count: int, dimensions: int) -> None:
    """Reject missing, nonfinite, zero, or incorrectly sized provider vectors."""
    if len(vectors) != count or any(
        len(vector) != dimensions
        or not all(math.isfinite(value) for value in vector)
        or not any(vector)
        for vector in vectors
    ):
        raise ProviderError("invalid_embedding_response")


class IngestionService:
    """Ingest PDFs with injected providers and persistence, without hidden API calls."""

    def __init__(
        self,
        settings: Settings,
        provider: EmbeddingProvider,
        repository: IngestionRepository,
    ) -> None:
        if provider.dimensions != EMBEDDING_DIMENSIONS:
            raise ValueError("provider dimensions must match the database schema")
        self._settings = settings
        self._provider = provider
        self._repository = repository
        self.profile = indexing_profile(settings, provider)

    def ingest(self, path: Path, metadata: CorpusDocument | None = None) -> IngestionResult:
        """Index a PDF or report a safe, explicit skip/failure without a partial write."""
        try:
            with path.open("rb") as stream:
                data = stream.read(self._settings.max_pdf_bytes + 1)
        except OSError:
            return IngestionResult(path.name, "failed", "file_unreadable")
        if len(data) > self._settings.max_pdf_bytes:
            return IngestionResult(path.name, "skipped", "pdf_too_large")
        doc_id = hashlib.sha256(data).hexdigest()
        if self._repository.contains(doc_id, self.profile):
            return IngestionResult(path.name, "skipped", "already_indexed", doc_id)
        try:
            pages = extract_pages(data, self._settings.max_pdf_pages)
        except IngestionError as exc:
            return IngestionResult(path.name, "skipped", str(exc), doc_id)
        chunks = chunk_pages(
            pages, self._settings.chunk_size_words, self._settings.chunk_overlap_words
        )
        vectors: list[list[float]] = []
        try:
            for start in range(0, len(chunks), self._settings.embedding_batch_size):
                batch = chunks[start : start + self._settings.embedding_batch_size]
                batch_vectors = self._provider.embed([chunk.text for chunk in batch])
                validate_vectors(batch_vectors, len(batch), self._provider.dimensions)
                vectors.extend(batch_vectors)
        except ProviderError:
            # Do not trust arbitrary provider exception messages to be safe to display.
            return IngestionResult(path.name, "failed", "embedding_failed", doc_id)
        inserted = self._repository.save(
            doc_id, self.profile, path.name, metadata, pages, chunks, vectors
        )
        if not inserted:
            return IngestionResult(path.name, "skipped", "already_indexed", doc_id)
        return IngestionResult(
            path.name,
            "indexed",
            "ok",
            doc_id,
            len(pages),
            inserted,
            sum(not page.text for page in pages),
        )
