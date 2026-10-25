"""Separate the model's strict JSON contract from server-verified API citations."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnswerReason = Literal[
    "supported",
    "no_retrieval",
    "weak_retrieval",
    "context_limit",
    "model_unsupported",
    "invalid_citations",
]
GenerationMode = Literal["model", "scripted", "no_model"]


class ModelCitation(BaseModel):
    """Accept only a document identity, physical PDF page, and exact quoted passage."""

    model_config = ConfigDict(extra="forbid", strict=True)
    doc_id: str = Field(min_length=1)
    page: int = Field(gt=0)
    quote: str = Field(min_length=1)


class ModelAnswer(BaseModel):
    """Require the agreed JSON shape; no model-provided source URLs or titles are trusted."""

    model_config = ConfigDict(extra="forbid", strict=True)
    answer: str
    citations: list[ModelCitation]
    supported: bool


class VerifiedCitation(BaseModel):
    """Attach authoritative metadata from a retrieved chunk after quote verification."""

    doc_id: str
    page: int
    quote: str
    document_title: str
    source: str
    source_url: str | None
    chunk_id: int
    chunk_index: int


class CitationVerification(BaseModel):
    """Keep raw proposed/valid counts before refusing or deduplicating citations."""

    proposed: int = 0
    valid: int = 0


class AskResponse(BaseModel):
    """Return a checked answer or a fixed refusal, with explicit generation provenance."""

    answer: str
    citations: list[VerifiedCitation]
    supported: bool
    reason: AnswerReason
    mode: GenerationMode
    verification: CitationVerification
