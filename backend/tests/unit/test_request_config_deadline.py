import threading
import time
from contextlib import contextmanager
from unittest.mock import Mock

import httpx
import pytest
from app.api.ask import get_answer_service
from app.api.search import get_search_service
from app.deadlines import remaining_timeout, request_budget
from app.errors import RequestDeadlineError
from app.main import create_app
from app.providers.transport import post_provider_json
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError


def test_public_config_has_one_authoritative_limit_and_no_secrets(settings, monkeypatch):
    engine = Mock()
    monkeypatch.setattr("app.main.create_db_engine", lambda _: engine)
    config = settings.model_copy(
        update={
            "max_query_characters": 7,
            "search_strategy": "keyword",
            "search_k": 1,
            "search_max_k": 3,
            "gemini_api_key": SecretStr("do-not-expose"),
        }
    )
    with TestClient(create_app(config)) as client:
        response = client.get("/config")
    assert response.status_code == 200
    assert response.json() == {
        "max_query_characters": 7,
        "search_strategy": "keyword",
        "search_k": 1,
        "search_max_k": 3,
    }
    assert "do-not-expose" not in response.text
    engine.connect.assert_not_called()
    engine.dispose.assert_called_once()


@pytest.mark.parametrize(
    "endpoint,dependency,method",
    [("/search", get_search_service, "search"), ("/ask", get_answer_service, "ask")],
)
def test_deadline_responds_before_worker_finishes_and_defers_resource_cleanup(
    settings,
    endpoint,
    dependency,
    method,
):
    started, release, closed = threading.Event(), threading.Event(), threading.Event()
    service = Mock()

    def blocked(*_):
        started.set()
        release.wait(timeout=2)

    getattr(service, method).side_effect = blocked

    @contextmanager
    def scope():
        try:
            yield service
        finally:
            closed.set()

    app = create_app(settings.model_copy(update={"request_deadline_seconds": 0.2}))
    app.dependency_overrides[dependency] = lambda: scope
    with TestClient(app) as client:
        try:
            response = client.post(endpoint, json={"query": "private query"})
            assert response.status_code == 504
            assert response.json()["error"]["code"] == "request_timeout"
            assert "private query" not in response.text
            assert started.is_set() and not closed.is_set()
        finally:
            release.set()
        assert closed.wait(timeout=1)


def test_provider_phase_timeout_respects_budget_and_context_does_not_leak(settings):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with request_budget(time.monotonic() + 10):
            post_provider_json(client, "https://example.test", SecretStr("test-only"), {}, settings)
    assert 0 < requests[0].extensions["timeout"]["read"] <= 10
    assert remaining_timeout(30) == 30


def test_expired_budget_restores_context_and_never_calls_provider(settings):
    with pytest.raises(RequestDeadlineError), request_budget(time.monotonic() - 1):
        raise AssertionError("expired scope cannot begin")
    assert remaining_timeout(30) == 30


def test_backoff_cannot_outlive_the_remaining_budget(settings):
    sleep, requests = Mock(), []

    def handle(request):
        requests.append(request)
        return httpx.Response(503)

    config = settings.model_copy(
        update={"provider_backoff_seconds": 20, "provider_max_backoff_seconds": 30}
    )
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with request_budget(time.monotonic() + 10), pytest.raises(RequestDeadlineError):
            post_provider_json(
                client, "https://example.test", SecretStr("test-only"), {}, config, sleep
            )
    assert len(requests) == 1
    sleep.assert_not_called()


def test_proxy_margin_is_validated_even_when_provider_retry_timeouts_increase():
    from app.settings import Settings

    assert Settings(provider_timeout_seconds=120).request_deadline_seconds == 90
    assert (
        Settings(request_deadline_seconds=90, proxy_timeout_seconds=95).proxy_timeout_seconds == 95
    )
    for changes in (
        {"request_deadline_seconds": 0},
        {"proxy_timeout_seconds": 94},
        {"request_deadline_seconds": 120},
    ):
        with pytest.raises(ValidationError):
            Settings(**changes)


@pytest.mark.parametrize("endpoint", ["/ask", "/search"])
def test_invalid_unicode_request_is_a_sanitized_validation_error(settings, endpoint):
    with TestClient(create_app(settings)) as client:
        response = client.post(
            endpoint, content='{"query":"\\ud800"}', headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 422 and "Traceback" not in response.text
