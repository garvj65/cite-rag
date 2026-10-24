import pytest
from app.ingestion.chunk import chunk_pages
from app.ingestion.extract import ExtractedPage, clean_text


@pytest.mark.parametrize(
    ("text", "size", "overlap", "expected"),
    [
        ("", 3, 1, []),
        ("a b", 3, 1, ["a b"]),
        ("a b c", 3, 1, ["a b c"]),
        ("a b c d", 3, 1, ["a b c", "c d"]),
        ("a b c d e", 3, 1, ["a b c", "c d e"]),
        ("a b c d e f", 3, 0, ["a b c", "d e f"]),
        ("a b c", 1, 0, ["a", "b", "c"]),
        ("a b c d", 3, 2, ["a b c", "b c d"]),
    ],
)
def test_chunk_boundaries(text, size, overlap, expected):
    chunks = chunk_pages([ExtractedPage(1, text)], size, overlap)
    assert [chunk.text for chunk in chunks] == expected
    assert all(text[chunk.start_char : chunk.end_char] == chunk.text for chunk in chunks)


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (2, 2), (2, -1), (2, 3)])
def test_invalid_chunk_settings(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([], size, overlap)


def test_page_tracking_overlap_and_unicode():
    pages = [
        ExtractedPage(1, "alpha beta gamma delta"),
        ExtractedPage(2, ""),
        ExtractedPage(3, "नमस्ते café 🙂 final"),
    ]
    chunks = chunk_pages(pages, 3, 1)
    assert [(chunk.page_number, chunk.chunk_index) for chunk in chunks] == [
        (1, 0),
        (1, 1),
        (3, 0),
        (3, 1),
    ]
    assert chunks[0].text.split()[-1] == chunks[1].text.split()[0]
    assert chunks[2].text == "नमस्ते café 🙂"
    assert clean_text(" A\n\t B\x00  café\u00a0🙂 ") == "A B café 🙂"


def test_every_word_is_covered_without_crossing_pages():
    text = " ".join(str(index) for index in range(100))
    chunks = chunk_pages([ExtractedPage(7, text)], 17, 4)
    covered = {word for chunk in chunks for word in chunk.text.split()}
    assert covered == set(text.split())
    assert all(chunk.page_number == 7 and len(chunk.text.split()) <= 17 for chunk in chunks)
