"""Verify only against the exact retrieved passages supplied in the model prompt."""

from collections.abc import Sequence

from app.answering.models import ModelCitation, VerifiedCitation
from app.retrieval.models import SearchHit


def normalize_whitespace(text: str) -> str:
    """Collapse Unicode whitespace without changing case, punctuation, or words."""
    return " ".join(text.split())


def verify_citation(
    citation: ModelCitation, passages: Sequence[SearchHit]
) -> VerifiedCitation | None:
    """Resolve a nonempty quote to one included chunk on the exact document and page."""
    quote = normalize_whitespace(citation.quote)
    if not quote:
        return None
    for hit in passages:
        if (
            citation.doc_id == hit.doc_id
            and citation.page == hit.page
            and quote in normalize_whitespace(hit.text)
        ):
            return VerifiedCitation(
                doc_id=hit.doc_id,
                page=hit.page,
                quote=quote,
                document_title=hit.document_title,
                source=hit.source,
                source_url=hit.source_url,
                chunk_id=hit.chunk_id,
                chunk_index=hit.chunk_index,
            )
    return None
