"""Typed retrieval results shared by strategies, the API, and later evaluation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.settings import RetrievalStrategy

ScoreType = Literal["cosine_similarity", "fts_rank", "rrf"]


class SearchHit(BaseModel):
    """Return one stored chunk with its score and source metadata."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    chunk_id: int
    doc_id: str
    document_title: str
    source: str
    source_url: str | None
    page: int
    chunk_index: int
    text: str
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None


class SearchResponse(BaseModel):
    """Describe the selected ranking method, index profile, and top passages."""

    strategy: RetrievalStrategy
    k: int
    profile: str
    score_type: ScoreType
    results: list[SearchHit]
