"""Small relational schema; completed document writes are transactionally visible."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.settings import EMBEDDING_DIMENSIONS


class Base(DeclarativeBase):
    """Own SQLAlchemy metadata used by Alembic."""


class Document(Base):
    """Store immutable PDF identity and human-readable source metadata."""

    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(primary_key=True)  # SHA-256 of original PDF bytes.
    title: Mapped[str]
    filename: Mapped[str]
    source: Mapped[str]
    source_url: Mapped[str | None]
    page_count: Mapped[int]
    __table_args__ = (CheckConstraint("page_count > 0", name="positive_page_count"),)


class Page(Base):
    """Keep canonical extracted text and physical PDF page numbering."""

    __tablename__ = "pages"
    doc_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    page_number: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    __table_args__ = (CheckConstraint("page_number > 0", name="positive_page_number"),)


class Chunk(Base):
    """Store passages and embeddings partitioned by their indexing fingerprint."""

    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str]
    page_number: Mapped[int]
    profile: Mapped[str] = mapped_column(index=True)
    chunk_index: Mapped[int]
    start_char: Mapped[int]
    end_char: Mapped[int]
    text: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    __table_args__ = (
        ForeignKeyConstraint(
            ["doc_id", "page_number"], ["pages.doc_id", "pages.page_number"], ondelete="CASCADE"
        ),
        UniqueConstraint(
            "doc_id", "profile", "page_number", "chunk_index", name="unique_chunk_position"
        ),
        CheckConstraint("chunk_index >= 0", name="nonnegative_chunk_index"),
        CheckConstraint("start_char >= 0 AND end_char > start_char", name="valid_chunk_offsets"),
    )
