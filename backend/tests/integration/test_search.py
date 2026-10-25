from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.db.models import Document
from app.db.repository import PostgresIngestionRepository
from app.ingestion.manifest import CorpusDocument
from app.ingestion.service import IngestionService, indexing_profile
from app.main import create_app
from app.providers.fakes import HashEmbeddingProvider
from app.retrieval.repository import PostgresSearchRepository
from app.retrieval.service import SearchService
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def corpus(engine, settings, pdf_bytes, tmp_path):
    config = settings.model_copy(update={"embedding_provider": "fake"})
    service = IngestionService(config, HashEmbeddingProvider(), PostgresIngestionRepository(engine))
    identities = []
    for index, text in enumerate(["apple apple orchard", "apple orchard", "ocean whale"]):
        path = tmp_path / f"fixture-{index}.pdf"
        path.write_bytes(pdf_bytes([text]))
        metadata = CorpusDocument(
            title=f"Fixture {index}",
            source="Offline test fixture",
            url=f"https://example.test/{index}.pdf",
        )
        result = service.ingest(path, metadata)
        assert result.status == "indexed"
        identities.append(result.doc_id)
    return config, identities


@pytest.mark.parametrize("strategy", ["vector", "keyword", "hybrid"])
def test_real_postgres_ranking_using_fake_embeddings(engine, corpus, strategy):
    config, identities = corpus
    service = SearchService(config, PostgresSearchRepository(engine), HashEmbeddingProvider)
    response = service.search("apple", strategy, 2)
    assert [hit.doc_id for hit in response.results] == identities[:2]
    assert response.results[0].score > response.results[1].score
    assert response.results[0].document_title == "Fixture 0"
    assert response.results[0].source_url == "https://example.test/0.pdf"
    assert all(hit.page == 1 and hit.chunk_index == 0 for hit in response.results)
    assert len(service.search("apple", strategy, 1).results) == 1


def test_keyword_stemming_phrases_stopwords_and_safe_query_parsing(engine, corpus):
    config, identities = corpus
    repository = PostgresSearchRepository(engine)
    profile = indexing_profile(config)
    assert len(repository.keyword_search(profile, "apples", 5)) == 2
    assert len(repository.keyword_search(profile, '"apple orchard"', 5)) == 2
    for query in ("the and", '""" )( query <->', "'); DROP TABLE documents; --"):
        assert repository.keyword_search(profile, query, 5) == []
    assert repository.keyword_search(profile, "no_such_word_in_fixture", 5) == []
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Document)) == len(identities)


def test_all_strategies_isolate_index_profiles(engine, corpus, pdf_bytes, tmp_path):
    config, identities = corpus
    different = config.model_copy(update={"chunk_size_words": 6})
    path = tmp_path / "different-profile.pdf"
    path.write_bytes(pdf_bytes(["apple apple apple apple"]))
    IngestionService(
        different, HashEmbeddingProvider(), PostgresIngestionRepository(engine)
    ).ingest(path)
    repository = PostgresSearchRepository(engine)
    for strategy in ("vector", "keyword", "hybrid"):
        result = SearchService(config, repository, HashEmbeddingProvider).search(
            "apple", strategy, 5
        )
        assert all(hit.doc_id in identities for hit in result.results)
    assert not repository.has_profile("missing-profile")
    missing = config.model_copy(update={"chunk_size_words": 7})
    assert SearchService(missing, repository, HashEmbeddingProvider).search("apple").results == []


def test_real_ranking_ties_are_repeatable(engine, settings, pdf_bytes, tmp_path):
    config = settings.model_copy(update={"embedding_provider": "fake"})
    ingestion = IngestionService(
        config, HashEmbeddingProvider(), PostgresIngestionRepository(engine)
    )
    identities = []
    for index, content in enumerate(["apple orchard", "orchard apple"]):
        path = tmp_path / f"tie-{index}.pdf"
        path.write_bytes(pdf_bytes([content]))
        identities.append(ingestion.ingest(path).doc_id)
    service = SearchService(config, PostgresSearchRepository(engine), HashEmbeddingProvider)
    for strategy in ("vector", "keyword", "hybrid"):
        for _ in range(2):
            assert [hit.doc_id for hit in service.search("apple", strategy).results] == sorted(
                identities
            )


@pytest.mark.parametrize("strategy", ["vector", "keyword", "hybrid"])
def test_api_dependency_lifecycle_with_real_postgres(engine, corpus, strategy):
    config, identities = corpus
    config = config.model_copy(
        update={"database_url": SecretStr(engine.url.render_as_string(hide_password=False))}
    )
    with TestClient(create_app(config)) as client:
        response = client.post("/search", json={"query": "apple", "strategy": strategy, "k": 2})
        assert response.status_code == 200
        assert [hit["doc_id"] for hit in response.json()["results"]] == identities[:2]


def test_keyword_migration_backfills_existing_m1_chunks(engine, settings, pdf_path):
    migration = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.downgrade(migration, "0001")
    config = settings.model_copy(update={"embedding_provider": "fake"})
    try:
        result = IngestionService(
            config, HashEmbeddingProvider(), PostgresIngestionRepository(engine)
        ).ingest(pdf_path)
        assert result.status == "indexed"
    finally:
        command.upgrade(migration, "head")
    hits = PostgresSearchRepository(engine).keyword_search(indexing_profile(config), "alpha", 5)
    assert hits and hits[0].doc_id == result.doc_id
