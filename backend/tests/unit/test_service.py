import pytest
from app.errors import ProviderError, ProviderTimeoutError
from app.ingestion.service import IngestionService, indexing_profile, validate_vectors
from app.providers.fakes import HashEmbeddingProvider
from app.settings import EMBEDDING_DIMENSIONS


def test_ingestion_batches_and_renamed_duplicate(settings, repository, pdf_path, tmp_path):
    class RecordingEmbedder(HashEmbeddingProvider):
        def __init__(self):
            super().__init__()
            self.batches = []

        def embed(self, texts):
            self.batches.append(list(texts))
            return super().embed(texts)

    fake = RecordingEmbedder()
    service = IngestionService(settings, fake, repository)
    first = service.ingest(pdf_path)
    assert (first.status, first.pages, first.chunks) == ("indexed", 2, 3)
    assert [len(batch) for batch in fake.batches] == [2, 1]
    renamed = tmp_path / "renamed.pdf"
    renamed.write_bytes(pdf_path.read_bytes())
    second = service.ingest(renamed)
    assert second.reason == "already_indexed" and first.doc_id == second.doc_id
    assert repository.saves == 1 and len(fake.batches) == 2


def test_index_profiles_separate_settings_and_providers(settings, repository, pdf_path):
    fake = HashEmbeddingProvider()
    original = IngestionService(settings, fake, repository)
    changed = IngestionService(
        settings.model_copy(update={"chunk_size_words": 6}), fake, repository
    )
    assert original.profile != changed.profile
    assert original.ingest(pdf_path).status == changed.ingest(pdf_path).status == "indexed"

    class Alternate(HashEmbeddingProvider):
        @property
        def model_id(self):
            return "other/model"

    assert indexing_profile(settings, Alternate()) != original.profile


@pytest.mark.parametrize(
    "exception", [ProviderError("secret response"), ProviderTimeoutError("secret timeout")]
)
def test_provider_failure_has_no_partial_write(settings, repository, pdf_path, exception):
    class FailingEmbedder(HashEmbeddingProvider):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def embed(self, texts):
            self.calls += 1
            if self.calls == 2:
                raise exception
            return super().embed(texts)

    result = IngestionService(settings, FailingEmbedder(), repository).ingest(pdf_path)
    assert (result.status, result.reason) == ("failed", "embedding_failed")
    assert repository.saves == 0 and repository.rows == {}


@pytest.mark.parametrize(
    "vectors",
    [[], [[1.0]], [[0.0] * EMBEDDING_DIMENSIONS], [[float("inf")] * EMBEDDING_DIMENSIONS]],
)
def test_invalid_provider_vectors(vectors):
    with pytest.raises(ProviderError, match="invalid_embedding_response"):
        validate_vectors(vectors, 1, EMBEDDING_DIMENSIONS)


def test_provider_dimension_guard(settings, repository):
    with pytest.raises(ValueError, match="dimensions"):
        IngestionService(settings, HashEmbeddingProvider(8), repository)


def test_unreadable_and_oversized_files(settings, repository, tmp_path):
    service = IngestionService(
        settings.model_copy(update={"max_pdf_bytes": 2}), HashEmbeddingProvider(), repository
    )
    assert service.ingest(tmp_path / "absent.pdf").reason == "file_unreadable"
    large = tmp_path / "large.pdf"
    large.write_bytes(b"123")
    assert service.ingest(large).reason == "pdf_too_large"
    assert not repository.rows


def test_extraction_rejections_have_reasons(settings, repository, tmp_path):
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")
    result = IngestionService(settings, HashEmbeddingProvider(), repository).ingest(path)
    assert (result.status, result.reason) == ("skipped", "empty_pdf")


def test_concurrent_duplicate_return_and_empty_page_count(
    settings, repository, pdf_path, pdf_bytes, monkeypatch
):
    monkeypatch.setattr(repository, "save", lambda *args: 0)
    service = IngestionService(settings, HashEmbeddingProvider(), repository)
    assert service.ingest(pdf_path).reason == "already_indexed"
    monkeypatch.undo()
    pdf_path.write_bytes(pdf_bytes(["first", "", "third"]))
    result = service.ingest(pdf_path)
    assert result.pages == 3 and result.empty_pages == 1 and result.chunks == 2


def test_invalid_vectors_from_provider_do_not_persist(settings, repository, pdf_path):
    class Broken(HashEmbeddingProvider):
        def embed(self, texts):
            return []

    result = IngestionService(settings, Broken(), repository).ingest(pdf_path)
    assert result.reason == "embedding_failed" and repository.saves == 0
