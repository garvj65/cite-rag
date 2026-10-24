import io
from unittest.mock import Mock

import pytest
from app.errors import IngestionError
from app.ingestion.extract import extract_pages
from pypdf import PdfWriter


@pytest.mark.parametrize(
    ("data", "reason"), [(b"", "empty_pdf"), (b"not a PDF", "pdf_extraction_failed")]
)
def test_bad_files(data, reason):
    with pytest.raises(IngestionError, match=reason):
        extract_pages(data, 500)


def test_zero_page_pdf():
    stream = io.BytesIO()
    PdfWriter().write(stream)
    with pytest.raises(IngestionError, match="empty_pdf"):
        extract_pages(stream.getvalue(), 500)


def test_no_text_pdf(pdf_bytes):
    with pytest.raises(IngestionError, match="no_extractable_text"):
        extract_pages(pdf_bytes(["", ""]), 500)


def test_scanned_image_only_pdf():
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    stream = io.BytesIO()
    canvas = Canvas(stream, invariant=True)
    canvas.drawImage(ImageReader(Image.new("RGB", (20, 20), "white")), 0, 0, 100, 100)
    canvas.save()
    with pytest.raises(IngestionError, match="no_extractable_text"):
        extract_pages(stream.getvalue(), 500)


def test_empty_pages_preserve_physical_numbering(pdf_bytes):
    pages = extract_pages(pdf_bytes(["first", "", "third"]), 500)
    assert [(page.page_number, page.text) for page in pages] == [
        (1, "first"),
        (2, ""),
        (3, "third"),
    ]


def test_page_limit(pdf_bytes):
    with pytest.raises(IngestionError, match="too_many_pages"):
        extract_pages(pdf_bytes(["first", "second"]), 1)


def test_encrypted_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("fixture-password")
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(IngestionError, match="encrypted_pdf"):
        extract_pages(stream.getvalue(), 500)


def test_partial_extraction_failure_rejects_entire_document(monkeypatch):
    good, bad = Mock(), Mock()
    good.extract_text.return_value = "extractable first page"
    bad.extract_text.side_effect = RuntimeError("must not escape")
    reader = Mock(is_encrypted=False, pages=[good, bad])
    monkeypatch.setattr("app.ingestion.extract.PdfReader", lambda *_: reader)
    with pytest.raises(IngestionError, match="^pdf_extraction_failed$"):
        extract_pages(b"fixture", 500)
