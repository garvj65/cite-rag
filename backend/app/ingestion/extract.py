"""PDF extraction with one-based physical page numbers and conservative cleaning."""

import io
from dataclasses import dataclass

from pypdf import PdfReader

from app.errors import IngestionError


@dataclass(frozen=True)
class ExtractedPage:
    """Store canonical page text, including empty pages, without renumbering."""

    page_number: int
    text: str


def clean_text(text: str) -> str:
    """Normalize whitespace and remove NULs without changing words or punctuation."""
    return " ".join(text.replace("\x00", "").split())


def extract_pages(data: bytes, max_pages: int) -> list[ExtractedPage]:
    """Extract all pages or reject the whole PDF with a stable failure reason."""
    if not data:
        raise IngestionError("empty_pdf")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise IngestionError("encrypted_pdf")
        if not reader.pages:
            raise IngestionError("empty_pdf")
        if len(reader.pages) > max_pages:
            raise IngestionError("too_many_pages")
        pages = [
            ExtractedPage(index, clean_text(page.extract_text() or ""))
            for index, page in enumerate(reader.pages, start=1)
        ]
    except IngestionError:
        raise
    except Exception:
        # PDF parsers can raise multiple implementation-specific exceptions.
        raise IngestionError("pdf_extraction_failed") from None
    if not any(page.text for page in pages):
        raise IngestionError("no_extractable_text")
    return pages
