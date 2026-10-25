import json
from contextlib import ExitStack
from unittest.mock import Mock

import httpx
import pytest
from app.answering.models import ModelAnswer
from app.errors import (
    ModelOutputError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
)
from app.providers.chat import HTTPChatProvider
from app.providers.factory import create_embedding_provider, create_llm_provider
from app.providers.fakes import ScriptedLLMProvider
from pydantic import SecretStr


def config(settings, **updates):
    return settings.model_copy(
        update={
            "enable_real_providers": True,
            "gemini_api_key": SecretStr("test-only-key"),
            "openai_api_key": SecretStr("test-only-key"),
            "openai_chat_model": "configured-model",
            **updates,
        }
    )


def completion(content='{"answer":"","citations":[],"supported":false}', finish="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


@pytest.mark.parametrize("vendor", ["gemini", "openai"])
def test_chat_provider_sends_separate_roles_and_strict_schema(settings, vendor):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=completion())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = HTTPChatProvider(config(settings, llm_provider=vendor), client)
        assert (
            json.loads(provider.generate("trusted instructions", "untrusted passage"))["supported"]
            is False
        )
    request = calls[0]
    body = json.loads(request.content)
    assert request.url.path.endswith("/chat/completions")
    assert request.url.host == (
        "api.openai.com" if vendor == "openai" else "generativelanguage.googleapis.com"
    )
    assert body["messages"] == [
        {"role": "system", "content": "trusted instructions"},
        {"role": "user", "content": "untrusted passage"},
    ]
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == ModelAnswer.model_json_schema()
    assert body["max_completion_tokens"] == settings.chat_max_completion_tokens
    assert "test-only-key" not in str(request.url)


@pytest.mark.parametrize(
    "updates",
    [
        {"enable_real_providers": False},
        {"llm_provider": "fake"},
        {"gemini_api_key": SecretStr("")},
        {"llm_provider": "openai", "openai_chat_model": ""},
    ],
)
def test_chat_configuration_is_explicit(settings, updates):
    with pytest.raises(ProviderConfigurationError):
        HTTPChatProvider(config(settings, **updates), Mock())


def test_chat_retries_transient_http_failures(settings):
    calls, delays = [], []

    def handle(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) < 3 else 200, json=completion())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        HTTPChatProvider(config(settings), client, delays.append).generate("system", "data")
    assert delays == [1, 2] and len(calls) == 3


def test_chat_timeout_is_bounded_and_sanitized(settings):
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("private", request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderTimeoutError, match="^provider_timeout$"):
            HTTPChatProvider(config(settings), client, lambda _: None).generate("system", "data")
    assert len(calls) == settings.provider_max_attempts


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        completion(finish="length"),
        completion(content=None),
        {"choices": [{"message": {"content": ["not text"]}, "finish_reason": "stop"}]},
        {"choices": completion()["choices"] * 2},
    ],
)
def test_malformed_or_truncated_chat_response_is_not_retried(settings, payload):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=payload)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ModelOutputError):
            HTTPChatProvider(config(settings), client).generate("system", "data")
    assert len(calls) == 1


def test_provider_refusal_is_not_misrepresented_as_a_missing_document(settings):
    payload = {"choices": [{"message": {"refusal": "policy refusal"}, "finish_reason": "stop"}]}
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as c:
        with pytest.raises(ProviderError, match="chat_provider_refused_request"):
            HTTPChatProvider(config(settings), c).generate("system", "data")


def test_chat_factory_fake_and_real_cleanup(settings, monkeypatch):
    fake_settings = settings.model_copy(update={"llm_provider": "fake"})
    with ExitStack() as stack:
        fake = create_llm_provider(fake_settings, stack)
        assert isinstance(fake, ScriptedLLMProvider)
        assert json.loads(fake.generate("system", "data"))["supported"] is False
        with pytest.raises(ProviderConfigurationError):
            create_llm_provider(settings, stack)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion()))
    )
    monkeypatch.setattr("app.providers.factory.httpx.Client", lambda: client)
    with ExitStack() as stack:
        assert isinstance(create_llm_provider(config(settings), stack), HTTPChatProvider)
        assert not client.is_closed
    assert client.is_closed


@pytest.mark.parametrize("factory", [create_embedding_provider, create_llm_provider])
def test_missing_key_fails_before_http_client_initialization(settings, monkeypatch, factory):
    def forbidden():
        raise AssertionError("HTTP clients must not initialize before configuration validation")

    monkeypatch.setattr("app.providers.factory.httpx.Client", forbidden)
    missing = settings.model_copy(update={"enable_real_providers": True})
    with ExitStack() as stack, pytest.raises(ProviderConfigurationError):
        factory(missing, stack)
