import httpx
import pytest
from app.ingestion.manifest import CorpusDocument, CorpusManifest, load_manifest
from pydantic import ValidationError

from scripts.download_corpus import download_document, main


@pytest.fixture
def document():
    return CorpusDocument(
        title="Public / PDF", url="https://example.test/doc.pdf", source="Fixture"
    )


def test_manifest_validation_safe_filename_and_round_trip(document, tmp_path):
    assert document.filename.startswith("public-pdf-")
    assert document.filename.endswith(".pdf") and "/" not in document.filename
    path = tmp_path / "manifest.yaml"
    path.write_text(
        "documents:\n  - title: Title\n    url: https://example.test/a\n    source: NIST\n"
    )
    assert load_manifest(path).documents[0].source == "NIST"
    with pytest.raises(ValidationError, match="duplicate"):
        CorpusManifest(documents=[document, document])
    with pytest.raises(ValidationError, match="HTTPS"):
        CorpusManifest(documents=[document.model_copy(update={"url": httpx.URL("http://host/")})])
    with pytest.raises(ValidationError):
        CorpusDocument(title="x", url="file:///etc/passwd", source="x")
    assert CorpusDocument(title="你好", url="https://example.test", source="x").filename.startswith(
        "document-"
    )


def test_atomic_download_and_cached_rerun(document, tmp_path):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, content=b"%PDF-fixture")

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        assert download_document(document, tmp_path, client, 100) == "downloaded"
        assert download_document(document, tmp_path, client, 100) == "already_downloaded"
    assert len(calls) == 1
    assert (tmp_path / document.filename).read_bytes() == b"%PDF-fixture"
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize(
    ("content", "limit", "reason"),
    [
        (b"%PDF-too-large", 5, "pdf_too_large"),
        (b"<html>error</html>", 100, "response_is_not_pdf"),
    ],
)
def test_failed_download_cleans_temp_and_preserves_old_file(
    document, tmp_path, content, limit, reason
):
    old = tmp_path / document.filename
    old.write_bytes(b"old incomplete file")
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    ) as c:
        with pytest.raises(ValueError, match=reason):
            download_document(document, tmp_path, c, limit)
    assert old.read_bytes() == b"old incomplete file" and not list(tmp_path.glob("*.part"))


def test_download_http_failure(document, tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(404))) as c:
        with pytest.raises(httpx.HTTPStatusError):
            download_document(document, tmp_path, c, 100)
    assert not list(tmp_path.glob("*.part"))


def test_downloader_cli_configuration_and_partial_failure(tmp_path, monkeypatch, capsys):
    assert main(["--manifest", str(tmp_path / "absent")]) == 2
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "documents:\n  - title: One\n    url: https://example.test/a\n    source: X\n"
        "  - title: Two\n    url: https://example.test/b\n    source: X\n"
    )

    def handle(request):
        return (
            httpx.Response(200, content=b"%PDF-fixture")
            if request.url.path == "/a"
            else httpx.Response(500)
        )

    client = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr("scripts.download_corpus.httpx.Client", lambda **_: client)
    assert main(["--manifest", str(manifest)]) == 1
    assert "One: downloaded" in capsys.readouterr().out
