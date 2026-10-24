import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.db.models import Chunk, Document, Page
from app.db.repository import PostgresIngestionRepository
from app.ingestion.chunk import TextChunk
from app.ingestion.extract import ExtractedPage
from app.ingestion.manifest import CorpusDocument
from app.ingestion.service import IngestionService
from app.providers.fakes import HashEmbeddingProvider
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    parsed = make_url(url)
    if parsed.host not in ("127.0.0.1", "localhost", "::1") or not (
        parsed.database and parsed.database.endswith("_test")
    ):
        pytest.fail("TEST_DATABASE_URL must name a local disposable database ending in _test")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")
    db = create_engine(url)
    yield db
    db.dispose()
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous


@pytest.fixture(autouse=True)
def clean_database(engine):
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE chunks, pages, documents RESTART IDENTITY CASCADE"))


def test_real_pgvector_ingestion_idempotency_and_profile_isolation(engine, settings, pdf_path):
    repository = PostgresIngestionRepository(engine)
    fake = HashEmbeddingProvider()
    service = IngestionService(settings, fake, repository)
    assert not repository.contains("missing", service.profile)
    first = service.ingest(pdf_path)
    assert (first.status, first.chunks) == ("indexed", 3)
    assert service.ingest(pdf_path).reason == "already_indexed"
    changed = IngestionService(
        settings.model_copy(update={"chunk_size_words": 6}), fake, repository
    )
    assert changed.ingest(pdf_path).status == "indexed"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Document)) == 1
        assert session.scalar(select(func.count()).select_from(Page)) == 2
        assert session.scalar(select(func.count()).select_from(Chunk)) == 6
        chunk = session.scalars(select(Chunk).order_by(Chunk.id)).first()
        assert chunk is not None and len(chunk.embedding) == 1536
        assert session.scalar(select(func.vector_dims(Chunk.embedding)).limit(1)) == 1536


def test_concurrent_ingestion_commits_exactly_one_copy(engine, settings, pdf_path):
    def ingest():
        return IngestionService(
            settings, HashEmbeddingProvider(), PostgresIngestionRepository(engine)
        ).ingest(pdf_path)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ingest(), range(2)))
    assert sorted(result.status for result in results) == ["indexed", "skipped"]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Chunk)) == 3


def test_atomic_rollback_on_invalid_chunk(engine):
    repository = PostgresIngestionRepository(engine)
    pages = [ExtractedPage(1, "hello")]
    bad = TextChunk(1, 0, -1, 5, "hello")
    vector = HashEmbeddingProvider().embed(["hello"])
    with pytest.raises(IntegrityError):
        repository.save("a" * 64, "profile", "file.pdf", None, pages, [bad], vector)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Document)) == 0
        assert session.scalar(select(func.count()).select_from(Page)) == 0
        assert session.scalar(select(func.count()).select_from(Chunk)) == 0


def test_save_duplicate_race_source_metadata_and_dimension_validation(engine):
    repository = PostgresIngestionRepository(engine)
    metadata = CorpusDocument(title="Original", source="NIST", url="https://example.test/file.pdf")
    pages, chunks = [ExtractedPage(1, "hello")], [TextChunk(1, 0, 0, 5, "hello")]
    vectors = HashEmbeddingProvider().embed(["hello"])
    assert repository.save("b" * 64, "profile", "file.pdf", metadata, pages, chunks, vectors) == 1
    assert repository.save("b" * 64, "profile", "renamed.pdf", None, pages, chunks, vectors) == 0
    with Session(engine) as session:
        document = session.get(Document, "b" * 64)
        assert document.title == "Original" and document.source_url == str(metadata.url)
    with pytest.raises(ValueError):
        repository.save("c" * 64, "profile", "file.pdf", None, pages, chunks, [])


def test_migration_downgrade_and_upgrade(engine):
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.downgrade(config, "base")
    assert "chunks" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert {"documents", "pages", "chunks"} <= set(inspect(engine).get_table_names())
