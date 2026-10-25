import pytest
from app.main import create_app
from app.settings import Settings
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_health_without_any_services():
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/ask", json={"query": ""}).status_code == 422


@pytest.mark.parametrize(
    "values",
    [
        {"chunk_size_words": 1, "chunk_overlap_words": 1},
        {"chunk_size_words": 0},
        {"provider_max_attempts": 0},
        {"provider_timeout_seconds": 0},
    ],
)
def test_settings_reject_invalid_limits(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_secret_values_are_redacted():
    settings = Settings(_env_file=None, gemini_api_key="example-secret-value")
    assert "example-secret-value" not in repr(settings)
    assert not settings.enable_real_providers
