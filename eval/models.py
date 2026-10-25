"""Serializable evaluation records with explicit missing metrics and experiment provenance."""

from app.answering.models import AskResponse
from app.settings import RetrievalStrategy
from pydantic import BaseModel, Field

from eval.schema import GoldPage


class EvaluationOptions(BaseModel):
    """Keep experiment defaults and bounds separate from application runtime settings."""

    strategy: RetrievalStrategy = "hybrid"
    k: int = Field(default=5, ge=1)
    seed: int = 42


class RetrievedPage(BaseModel):
    """Record ranking evidence without copying full document chunks into reports."""

    doc_id: str
    page: int
    chunk_id: int
    score: float


class EvaluationRow(BaseModel):
    """Retain each question's ranking, checked answer, sanitized failure, and latency."""

    id: str
    question: str
    answerable: bool
    gold_pages: list[GoldPage]
    retrieved: list[RetrievedPage]
    answer: AskResponse | None
    error: str | None
    recall: float | None
    reciprocal_rank: float | None
    retrieval_latency_ms: float
    latency_ms: float


class EvaluationSummary(BaseModel):
    """Expose aggregate metrics with the denominators needed to interpret them."""

    questions: int
    answerable: int
    unanswerable: int
    errors: int
    recall_at_k: float | None
    mrr: float | None
    citation_validity: float | None
    citations_proposed: int
    citations_valid: int
    refusal_accuracy: float | None
    correct_refusals: int
    latency_p50_ms: float | None
    latency_p95_ms: float | None


class EvaluationResult(BaseModel):
    """Bundle raw question records, aggregate measurements, and safe reproducibility metadata."""

    options: EvaluationOptions
    metadata: dict[str, object]
    summary: EvaluationSummary
    rows: list[EvaluationRow]
