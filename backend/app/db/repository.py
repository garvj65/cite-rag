"""PostgreSQL persistence for atomic and concurrent-safe PDF ingestion."""

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import Engine, create_engine, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document, Page
from app.ingestion.chunk import TextChunk
from app.ingestion.extract import ExtractedPage
from app.ingestion.manifest import CorpusDocument
from app.settings import Settings


class IngestionRepository(Protocol):
    """Expose the two database operations needed by the ingestion service."""

    def contains(self, doc_id: str, profile: str) -> bool:
        """Report whether a complete index of this PDF already exists."""
        ...

    def save(
        self,
        doc_id: str,
        profile: str,
        filename: str,
        metadata: CorpusDocument | None,
        pages: Sequence[ExtractedPage],
        chunks: Sequence[TextChunk],
        vectors: Sequence[list[float]],
    ) -> int:
        """Atomically store one document and return the number of newly inserted chunks."""
        ...


def create_db_engine(settings: Settings) -> Engine:
    """Construct a lazy PostgreSQL engine without logging connection parameters."""
    return create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True, echo=False)


class PostgresIngestionRepository:
    """Use uniqueness constraints rather than process-local duplicate tracking."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def contains(self, doc_id: str, profile: str) -> bool:
        """Check for committed chunks matching both PDF bytes and indexing settings."""
        with Session(self._engine) as session:
            return bool(
                session.scalar(
                    select(exists().where(Chunk.doc_id == doc_id, Chunk.profile == profile))
                )
            )

    def save(
        self,
        doc_id: str,
        profile: str,
        filename: str,
        metadata: CorpusDocument | None,
        pages: Sequence[ExtractedPage],
        chunks: Sequence[TextChunk],
        vectors: Sequence[list[float]],
    ) -> int:
        """Commit every page and chunk together, tolerating a concurrent identical write."""
        if len(chunks) != len(vectors) or not chunks:
            raise ValueError("each nonempty chunk batch requires one vector per chunk")
        with Session(self._engine) as session, session.begin():
            session.execute(
                insert(Document)
                .values(
                    id=doc_id,
                    title=metadata.title if metadata else filename,
                    filename=filename,
                    source=metadata.source if metadata else "local PDF",
                    source_url=str(metadata.url) if metadata else None,
                    page_count=len(pages),
                )
                .on_conflict_do_nothing(index_elements=[Document.id])
            )
            session.execute(
                insert(Page)
                .values(
                    [
                        {"doc_id": doc_id, "page_number": page.page_number, "text": page.text}
                        for page in pages
                    ]
                )
                .on_conflict_do_nothing(index_elements=[Page.doc_id, Page.page_number])
            )
            # Insert passages individually to keep bind count bounded even for long PDFs.
            inserted = 0
            for chunk, vector in zip(chunks, vectors, strict=True):
                result = session.scalar(
                    insert(Chunk)
                    .values(
                        doc_id=doc_id,
                        profile=profile,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                        text=chunk.text,
                        embedding=vector,
                    )
                    .on_conflict_do_nothing(constraint="unique_chunk_position")
                    .returning(Chunk.id)
                )
                inserted += int(result is not None)
            return inserted
