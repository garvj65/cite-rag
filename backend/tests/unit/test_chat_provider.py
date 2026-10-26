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
            "llm_provider": "openai",
            "gemini_api_key": SecretStr("test-only-key"),
            "openai_api_key": SecretStr("test-only-key"),
            "openai_chat_model": "configured-model",
            **updates,
        }
    )


def completion(content='{"answer":"","citations":[],"supported":false}', finish="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


def test_openai_chat_sends_separate_roles_and_strict_schema(settings):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=completion())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = HTTPChatProvider(config(settings), client)
        assert (
            json.loads(provider.generate("trusted instructions", "untrusted passage"))["supported"]
            is False
        )
    request = calls[0]
    body = json.loads(request.content)
    assert request.url.path.endswith("/chat/completions")
    assert request.url.host == "api.openai.com"
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
        {"llm_provider": "gemini", "gemini_api_key": SecretStr("")},
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


def gemini_completion(parts=None, finish="STOP"):
    return {
        "candidates": [
            {
                "content": {
                    "parts": parts
                    if parts is not None
                    else [{"text": '{"answer":"","citations":[],"supported":false}'}]
                },
                "finishReason": finish,
            }
        ]
    }


def test_native_gemini_chat_schema_roles_header_and_text_parts(settings):
    calls = []
    payload = gemini_completion(
        [
            {"text": "private thought", "thought": True},
            {"text": '{"answer":"","citations":[],'},
            {"text": '"supported":false}'},
        ]
    )

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=payload)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        text = HTTPChatProvider(config(settings, llm_provider="gemini"), client).generate(
            "trusted", "untrusted"
        )
    assert json.loads(text) == {"answer": "", "citations": [], "supported": False}
    request = calls[0]
    assert request.url.path.endswith(f"/models/{settings.gemini_chat_model}:generateContent")
    assert request.headers["x-goog-api-key"] == "test-only-key"
    assert "authorization" not in request.headers
    assert "test-only-key" not in str(request.url)
    body = json.loads(request.content)
    assert body["systemInstruction"] == {"parts": [{"text": "trusted"}]}
    assert body["contents"] == [{"role": "user", "parts": [{"text": "untrusted"}]}]
    assert body["generationConfig"] == {
        "responseFormat": {
            "text": {"mimeType": "APPLICATION_JSON", "schema": ModelAnswer.model_json_schema()}
        },
        "maxOutputTokens": settings.chat_max_completion_tokens,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"candidates": []},
        {"candidates": gemini_completion()["candidates"] * 2},
        gemini_completion(finish="MAX_TOKENS"),
        gemini_completion(parts=[]),
        gemini_completion(parts=[{"text": "hidden", "thought": True}]),
        gemini_completion(parts=[{"functionCall": {"name": "not_enabled"}}]),
        gemini_completion(parts=[{"text": 42}]),
        {"candidates": [{"finishReason": "STOP"}]},
    ],
)
def test_native_gemini_rejects_malformed_truncated_and_nontext_output(settings, payload):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=payload)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ModelOutputError):
            HTTPChatProvider(config(settings, llm_provider="gemini"), client).generate(
                "system", "data"
            )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"promptFeedback": {"blockReason": "SAFETY"}},
        gemini_completion(finish="SAFETY"),
        gemini_completion(finish="RECITATION"),
    ],
)
def test_native_gemini_provider_blocks_are_errors(settings, payload):
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(ProviderError, match="chat_provider_refused_request"):
            HTTPChatProvider(config(settings, llm_provider="gemini"), client).generate(
                "system", "data"
            )


def test_native_gemini_retries_transient_errors(settings):
    calls, delays = [], []

    def handle(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) == 1 else 200, json=gemini_completion())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        HTTPChatProvider(config(settings, llm_provider="gemini"), client, delays.append).generate(
            "system", "data"
        )
    assert len(calls) == 2 and delays == [1]
