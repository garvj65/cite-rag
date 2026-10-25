from unittest.mock import Mock

import pytest
from app.api.search import get_search_service
from app.errors import ProviderConfigurationError, ProviderError, ProviderTimeoutError
from app.main import create_app
from app.providers.fakes import HashEmbeddingProvider
from app.retrieval.models import SearchHit
from app.retrieval.service import SearchService
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


@pytest.fixture
def api(settings):
    config = settings.model_copy(update={"embedding_provider": "fake", "max_query_characters": 20})
    hit = SearchHit(
        chunk_id=9,
        doc_id="a" * 64,
        document_title="Fixture document",
        source="Fixture",
        source_url="https://example.test/a.pdf",
        page=2,
        chunk_index=0,
        text="stored exact passage",
        score=0.5,
    )
    repository = Mock()
    repository.has_profile.return_value = True
    repository.vector_search.return_value = [hit]
    repository.keyword_search.return_value = [hit]
    factory = Mock(return_value=HashEmbeddingProvider())
    service = SearchService(config, repository, factory)
    app = create_app(config)
    app.dependency_overrides[get_search_service] = lambda: service
    with TestClient(app) as client:
        yield client, repository, factory


@pytest.mark.parametrize("strategy", ["vector", "keyword", "hybrid"])
def test_api_returns_source_metadata_and_ranked_text(api, strategy):
    client, _, _ = api
    response = client.post("/search", json={"query": "passage", "strategy": strategy, "k": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == strategy and body["k"] == 1 and len(body["profile"]) == 64
    hit = body["results"][0]
    assert hit["doc_id"] == "a" * 64 and hit["page"] == 2 and hit["chunk_id"] == 9
    assert hit["text"] == "stored exact passage" and hit["source_url"].endswith("a.pdf")
    assert hit["document_title"] == "Fixture document"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"query": ""},
        {"query": " \t "},
        {"query": 12},
        {"query": "x" * 21},
        {"query": "x", "strategy": "other"},
        {"query": "x", "k": 0},
        {"query": "x", "k": 51},
        {"query": "x", "k": True},
        {"query": "x", "k": "5"},
        {"query": "x", "k": 1.5},
        {"query": "x", "unexpected": "field"},
    ],
)
def test_invalid_requests_are_rejected_and_not_reflected(api, payload):
    client, repository, factory = api
    response = client.post("/search", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_search_request"
    assert "xxxxxxxxxxxxxxxxxxxxx" not in response.text
    repository.has_profile.assert_not_called()
    factory.assert_not_called()


def test_empty_index_is_successful_and_uses_no_provider(api):
    client, repository, factory = api
    repository.has_profile.return_value = False
    response = client.post("/search", json={"query": "hello"})
    assert response.status_code == 200 and response.json()["results"] == []
    assert response.json()["strategy"] == "hybrid" and response.json()["k"] == 5
    factory.assert_not_called()


def test_keyword_works_without_constructing_embedding_provider(api):
    client, _, factory = api
    factory.side_effect = ProviderConfigurationError("no credentials")
    response = client.post("/search", json={"query": "hello", "strategy": "keyword"})
    assert response.status_code == 200
    factory.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ProviderConfigurationError("private API key"), 503, "provider_not_configured"),
        (ProviderTimeoutError("private request"), 504, "provider_timeout"),
        (ProviderError("private response body"), 502, "provider_failure"),
    ],
)
def test_provider_failures_are_explicit_and_sanitized(api, error, status, code):
    client, _, factory = api
    factory.side_effect = error
    response = client.post("/search", json={"query": "hello", "strategy": "vector"})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "private" not in response.text and "Traceback" not in response.text


def test_database_failure_hides_sql_and_credentials(api):
    client, repository, factory = api
    repository.has_profile.side_effect = OperationalError("private sql", {}, Exception("secret"))
    response = client.post("/search", json={"query": "hello"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert "secret" not in response.text and "private" not in response.text
    factory.assert_not_called()
