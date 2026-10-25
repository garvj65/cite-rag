import json

import pytest
from app.db.repository import PostgresIngestionRepository
from app.ingestion.service import IngestionService
from app.main import create_app
from app.providers.fakes import HashEmbeddingProvider
from fastapi.testclient import TestClient
from pydantic import SecretStr

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("strategy", ["vector", "keyword", "hybrid"])
def test_real_database_to_verified_answer_api(engine, settings, pdf_path, strategy):
    config = settings.model_copy(update={"embedding_provider": "fake", "llm_provider": "fake"})
    result = IngestionService(
        config, HashEmbeddingProvider(), PostgresIngestionRepository(engine)
    ).ingest(pdf_path)
    config = config.model_copy(
        update={
            "database_url": SecretStr(engine.url.render_as_string(hide_password=False)),
            "fake_llm_response": json.dumps(
                {
                    "answer": "The fixture includes alpha and beta.",
                    "citations": [{"doc_id": result.doc_id, "page": 1, "quote": "alpha beta"}],
                    "supported": True,
                }
            ),
        }
    )
    with TestClient(create_app(config)) as client:
        response = client.post("/ask", json={"query": "alpha beta", "strategy": strategy})
    assert response.status_code == 200
    data = response.json()
    assert data["supported"] and data["mode"] == "scripted" and data["reason"] == "supported"
    assert data["citations"][0]["doc_id"] == result.doc_id
    assert data["citations"][0]["page"] == 1 and data["citations"][0]["quote"] == "alpha beta"
    assert data["verification"] == {"proposed": 1, "valid": 1}


def test_empty_retrieval_refuses_without_configuring_any_model(engine, settings):
    config = settings.model_copy(
        update={
            "database_url": SecretStr(engine.url.render_as_string(hide_password=False)),
        }
    )
    with TestClient(create_app(config)) as client:
        response = client.post("/ask", json={"query": "question"})
    assert response.status_code == 200
    assert response.json()["reason"] == "no_retrieval"
    assert response.json()["mode"] == "no_model" and response.json()["citations"] == []
