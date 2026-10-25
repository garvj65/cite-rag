from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from app.answering.service import AnswerService
from app.api.ask import get_answer_service
from app.errors import ModelOutputError, ProviderError, ProviderTimeoutError
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ModelOutputError("private malformed output"), 502, "invalid_model_output"),
        (ProviderError("private provider response"), 502, "provider_failure"),
        (ProviderTimeoutError("private timeout"), 504, "provider_timeout"),
    ],
)
def test_answer_errors_are_not_document_refusals(settings, error, status, code):
    service = Mock(spec=AnswerService)
    service.ask.side_effect = error
    app = create_app(settings)
    app.dependency_overrides[get_answer_service] = lambda: lambda: nullcontext(service)
    with TestClient(app) as client:
        response = client.post("/ask", json={"query": "question"})
    assert response.status_code == status and response.json()["error"]["code"] == code
    assert "private" not in response.text and "Traceback" not in response.text


def test_ask_reuses_input_validation(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        for payload in ({"query": ""}, {"query": "x", "k": True}, {"query": "x", "extra": 1}):
            assert client.post("/ask", json=payload).status_code == 422
