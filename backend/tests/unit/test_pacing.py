import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from app.deadlines import request_budget
from app.errors import ProviderConfigurationError, RequestDeadlineError
from app.providers.chat import HTTPChatProvider
from app.providers.http import HTTPEmbeddingProvider
from app.providers.pacing import RequestPacer, get_pacer
from app.providers.transport import post_provider_json
from app.settings import Settings
from pydantic import SecretStr, ValidationError


class Clock:
    def __init__(self):
        self.now = 100.0
        self.delays = []

    def read(self):
        return self.now

    def sleep(self, delay):
        self.delays.append(delay)
        self.now += delay


def test_pacing_is_shared_by_endpoint_but_separate_between_models():
    assert get_pacer("chat", 12) is get_pacer("chat", 12)
    assert get_pacer("embedding", 90) is not get_pacer("chat", 12)
    assert get_pacer("disabled", 0) is None
    with pytest.raises(ValueError):
        RequestPacer(0)


def test_every_retry_and_subsequent_client_attempt_is_paced(settings):
    clock, calls = Clock(), []
    pacer = RequestPacer(12, clock.read)

    def handle(_):
        calls.append(clock.now)
        return httpx.Response(503 if len(calls) < 3 else 200)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        for _ in range(2):
            post_provider_json(
                client,
                "https://example.test",
                SecretStr("test"),
                {},
                settings,
                clock.sleep,
                pacer=pacer,
            )
    assert calls == [100, 105, 110, 115]
    # Backoff is retained and counted as elapsed time, not added again by the pacer.
    assert clock.delays == [1, 4, 2, 3, 5]


def test_embedding_inputs_are_charged_per_attempt_in_a_rolling_window():
    clock = Clock()
    pacer = RequestPacer(90, clock.read)
    starts = []
    for _ in range(10):
        pacer.wait(16, clock.sleep)
        starts.append(clock.now)
    assert starts[5] >= starts[0] + 60
    assert all(sum(16 for start in starts if end - 60 < start <= end) <= 90 for end in starts)
    with pytest.raises(ProviderConfigurationError):
        pacer.wait(91, clock.sleep)
    with pytest.raises(ProviderConfigurationError):
        pacer.wait(0, clock.sleep)


def test_concurrent_clients_cannot_spend_the_same_slot():
    clock = Clock()
    pacer = RequestPacer(12, clock.read)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: pacer.wait(1, clock.sleep), range(4)))
    assert clock.now == 115 and clock.delays == [5, 5, 5]


def test_pacing_cannot_outlive_api_budget_or_charge_an_unsent_attempt(settings, monkeypatch):
    clock, calls = Clock(), []
    monkeypatch.setattr("app.deadlines.time.monotonic", clock.read)
    pacer = RequestPacer(12, clock.read)
    pacer.wait(1, clock.sleep)
    with httpx.Client(transport=httpx.MockTransport(lambda _: calls.append(1))) as client:
        with request_budget(101), pytest.raises(RequestDeadlineError):
            post_provider_json(
                client,
                "https://example.test",
                SecretStr("test"),
                {},
                settings,
                clock.sleep,
                pacer=pacer,
            )
    assert not calls and not clock.delays
    pacer.wait(1, clock.sleep)
    assert clock.now == 105


def test_gemini_adapters_charge_batches_and_retries(settings, monkeypatch):
    clock, costs, models = Clock(), [], []

    class RecordingPacer(RequestPacer):
        def wait(self, units, sleep):
            costs.append(units)
            super().wait(units, sleep)

    pacer = RecordingPacer(90, clock.read)

    def select(endpoint, limit):
        models.append((endpoint, limit))
        return pacer

    monkeypatch.setattr("app.providers.http.get_pacer", select)
    monkeypatch.setattr("app.providers.chat.get_pacer", select)
    attempts = []

    def handle(request):
        attempts.append(request)
        if len(attempts) == 1:
            return httpx.Response(429)
        if "batchEmbedContents" in request.url.path:
            return httpx.Response(200, json={"embeddings": [{"values": [1.0] * 1536}] * 2})
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"answer":"","citations":[],"supported":false}'}]
                        },
                        "finishReason": "STOP",
                    }
                ]
            },
        )

    config = settings.model_copy(
        update={
            "enable_real_providers": True,
            "gemini_api_key": SecretStr("test-key"),
            "gemini_embedding_inputs_per_minute": 90,
            "gemini_chat_requests_per_minute": 12,
        }
    )
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        HTTPEmbeddingProvider(config, client, clock.sleep).embed(["first", "second"])
        assert not json.loads(HTTPChatProvider(config, client, clock.sleep).generate("s", "u"))[
            "supported"
        ]
    assert costs == [2, 2, 1]
    assert models[0][1] == 90 and models[1][1] == 12
    assert "gemini-3.5-flash-lite:generateContent" in models[1][0]


def test_batch_setting_must_fit_the_embedding_budget():
    with pytest.raises(ValidationError, match="embedding_batch_size"):
        Settings(_env_file=None, gemini_embedding_inputs_per_minute=10)
    assert Settings(_env_file=None, gemini_embedding_inputs_per_minute=0).embedding_batch_size == 16
