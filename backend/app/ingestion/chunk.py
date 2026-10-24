"""Deterministic word windows with exact character offsets into each page."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.ingestion.extract import ExtractedPage


@dataclass(frozen=True)
class TextChunk:
    """Represent one passage wholly contained in one physical PDF page."""

    page_number: int
    chunk_index: int
    start_char: int
    end_char: int
    text: str


def chunk_pages(pages: Sequence[ExtractedPage], size: int, overlap: int) -> list[TextChunk]:
    """Chunk nonempty pages, preserving overlap and avoiding redundant tail chunks."""
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("require size > 0 and 0 <= overlap < size")
    chunks: list[TextChunk] = []
    for page in pages:
        words = list(re.finditer(r"\S+", page.text))
        for index, start in enumerate(range(0, len(words), size - overlap)):
            end = min(start + size, len(words))
            start_char, end_char = words[start].start(), words[end - 1].end()
            chunks.append(
                TextChunk(
                    page.page_number, index, start_char, end_char, page.text[start_char:end_char]
                )
            )
            if end == len(words):
                break
    return chunks
