import io
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from app.ingestion.chunk import TextChunk
from app.ingestion.extract import ExtractedPage
from app.ingestion.manifest import CorpusDocument
from app.settings import Settings
from reportlab.pdfgen.canvas import Canvas


@pytest.fixture(autouse=True)
def isolate_proxy_environment(monkeypatch):
    # Host-specific proxies must not change offline test client construction.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


class MemoryRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], tuple[Sequence[ExtractedPage], Sequence[TextChunk]]] = {}
        self.saves = 0

    def contains(self, doc_id: str, profile: str) -> bool:
        return (doc_id, profile) in self.rows

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
        self.saves += 1
        if self.contains(doc_id, profile):
            return 0
        self.rows[doc_id, profile] = (pages, chunks)
        return len(chunks)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        chunk_size_words=5,
        chunk_overlap_words=2,
        embedding_batch_size=2,
        gemini_chat_requests_per_minute=0,
        gemini_embedding_inputs_per_minute=0,
    )


@pytest.fixture
def repository() -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def pdf_bytes() -> Callable[[list[str]], bytes]:
    def build(pages: list[str]) -> bytes:
        output = io.BytesIO()
        canvas = Canvas(output, invariant=True)
        for text in pages:
            if text:
                canvas.drawString(60, 700, text)
            canvas.showPage()
        canvas.save()
        return output.getvalue()

    return build


@pytest.fixture
def pdf_path(tmp_path: Path, pdf_bytes: Callable[[list[str]], bytes]) -> Path:
    path = tmp_path / "fixture.pdf"
    path.write_bytes(pdf_bytes(["alpha beta gamma delta epsilon zeta eta theta", "second page"]))
    return path
