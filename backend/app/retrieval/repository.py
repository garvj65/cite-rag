"""Exact vector search and indexed English full-text search in PostgreSQL."""

from collections.abc import Sequence

from sqlalchemy import Engine, exists, func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.retrieval.models import SearchHit


def _hit(chunk: Chunk, document: Document, score: float) -> SearchHit:
    return SearchHit(
        chunk_id=chunk.id,
        doc_id=chunk.doc_id,
        document_title=document.title,
        source=document.source,
        source_url=document.source_url,
        page=chunk.page_number,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        score=score,
    )


class PostgresSearchRepository:
    """Read profile-scoped passages without calling an embedding or chat provider."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def has_profile(self, profile: str) -> bool:
        """Check for indexed passages before spending provider quota on a question."""
        with Session(self._engine) as session:
            return bool(session.scalar(select(exists().where(Chunk.profile == profile))))

    def vector_search(self, profile: str, vector: Sequence[float], k: int) -> list[SearchHit]:
        """Return exact cosine neighbors; no approximate index changes baseline recall."""
        distance = Chunk.embedding.cosine_distance(list(vector))
        statement = (
            select(Chunk, Document, (1 - distance).label("score"))
            .join(Document, Document.id == Chunk.doc_id)
            .where(Chunk.profile == profile)
            .order_by(distance, Chunk.doc_id, Chunk.page_number, Chunk.chunk_index, Chunk.id)
            .limit(k)
        )
        with Session(self._engine) as session:
            return [
                _hit(chunk, document, float(score))
                for chunk, document, score in session.execute(statement)
            ]

    def keyword_search(self, profile: str, query: str, k: int) -> list[SearchHit]:
        """Parse user text safely with websearch_to_tsquery and rank matching chunks."""
        tsquery = func.websearch_to_tsquery("english", query)
        score = func.ts_rank_cd(Chunk.search_vector, tsquery)
        statement = (
            select(Chunk, Document, score.label("score"))
            .join(Document, Document.id == Chunk.doc_id)
            .where(Chunk.profile == profile, Chunk.search_vector.bool_op("@@")(tsquery))
            .order_by(score.desc(), Chunk.doc_id, Chunk.page_number, Chunk.chunk_index, Chunk.id)
            .limit(k)
        )
        with Session(self._engine) as session:
            return [
                _hit(chunk, document, float(value))
                for chunk, document, value in session.execute(statement)
            ]
