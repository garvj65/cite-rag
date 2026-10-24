"""Create immutable documents, canonical pages, and profile-scoped chunks."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Install pgvector and the M1 ingestion schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("page_count > 0", name="positive_page_count"),
    )
    op.create_table(
        "pages",
        sa.Column("doc_id", sa.String(), primary_key=True),
        sa.Column("page_number", sa.Integer(), primary_key=True),
        sa.Column("text", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["documents.id"], ondelete="CASCADE"),
        sa.CheckConstraint("page_number > 0", name="positive_page_number"),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_id", sa.String(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.ForeignKeyConstraint(
            ["doc_id", "page_number"], ["pages.doc_id", "pages.page_number"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "doc_id", "profile", "page_number", "chunk_index", name="unique_chunk_position"
        ),
        sa.CheckConstraint("chunk_index >= 0", name="nonnegative_chunk_index"),
        sa.CheckConstraint("start_char >= 0 AND end_char > start_char", name="valid_chunk_offsets"),
    )
    op.create_index("ix_chunks_profile", "chunks", ["profile"])


def downgrade() -> None:
    """Remove application tables while retaining the shared vector extension."""
    op.drop_table("chunks")
    op.drop_table("pages")
    op.drop_table("documents")
    # Leave the extension installed: other database objects may use it.
