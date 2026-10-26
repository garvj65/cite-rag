import math

import httpx
import pytest
from app.errors import ProviderError, ProviderTimeoutError
from app.providers.fakes import HashEmbeddingProvider, ScriptedLLMProvider
from app.providers.http import HTTPEmbeddingProvider
from app.settings import EMBEDDING_DIMENSIONS
from pydantic import SecretStr


def provider_settings(settings, **updates):
    return settings.model_copy(
        update={
            "enable_real_providers": True,
            "gemini_api_key": SecretStr("test-only-key"),
            "embedding_provider": "openai",
            "openai_api_key": SecretStr("test-only-openai-key"),
            **updates,
        }
    )


def embedding_payload(vector=None, index=0):
    return {"data": [{"index": index, "embedding": vector or [1.0] * EMBEDDING_DIMENSIONS}]}


def test_hash_fake_is_normalized_case_insensitive_and_stable():
    fake = HashEmbeddingProvider(32)
    first = fake.embed(["alpha BETA", "", "!!!"])
    assert first == HashEmbeddingProvider(32).embed(["ALPHA beta", "", "!!!"])
    assert first[1] == first[2]
    assert all(math.isclose(sum(v * v for v in vector), 1) for vector in first)
    assert fake.model_id == "fake/hash-word-count-v1"
    assert fake.embed([]) == []
    with pytest.raises(ValueError):
        HashEmbeddingProvider(0)


def test_scripted_llm_is_finite_and_records_prompts():
    fake = ScriptedLLMProvider(["response", ProviderError("failure")])
    assert fake.generate("system", "user") == "response"
    with pytest.raises(ProviderError, match="failure"):
        fake.generate("system", "user2")
    with pytest.raises(ProviderError, match="script_exhausted"):
        fake.generate("system", "user3")
    assert fake.calls == [("system", "user"), ("system", "user2"), ("system", "user3")]


def test_real_provider_requires_explicit_opt_in_and_key(settings):
    with httpx.Client() as client:
        with pytest.raises(ProviderError, match="real_providers_disabled"):
            HTTPEmbeddingProvider(settings, client)
        with pytest.raises(ProviderError, match="missing_provider_api_key"):
            HTTPEmbeddingProvider(
                settings.model_copy(update={"enable_real_providers": True}), client
            )


@pytest.mark.parametrize("vendor", ["gemini", "openai"])
def test_provider_contract_and_reordered_response(settings, vendor):
    calls = []

    def handle(request):
        calls.append(request)
        if vendor == "gemini":
            return httpx.Response(
                200,
                json={
                    "embeddings": [
                        {"values": [1.0] * EMBEDDING_DIMENSIONS},
                        {"values": [2.0] * EMBEDDING_DIMENSIONS},
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [2.0] * EMBEDDING_DIMENSIONS},
                    {"index": 0, "embedding": [1.0] * EMBEDDING_DIMENSIONS},
                ]
            },
        )

    config = provider_settings(
        settings, embedding_provider=vendor, openai_api_key=SecretStr("test-only-openai-key")
    )
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = HTTPEmbeddingProvider(config, client)
        assert provider.embed([]) == []
        vectors = provider.embed(["first", "second"])
    assert vectors[0][0] == 1 and vectors[1][0] == 2
    assert len(calls) == 1 and provider.model_id.startswith(f"{vendor}/")
    assert calls[0].url.host == (
        "api.openai.com" if vendor == "openai" else "generativelanguage.googleapis.com"
    )
    if vendor == "openai":
        assert b'"dimensions":1536' in calls[0].content
    else:
        import json

        body = json.loads(calls[0].content)
        assert calls[0].url.path.endswith("/models/gemini-embedding-2:batchEmbedContents")
        assert calls[0].headers["x-goog-api-key"] == "test-only-key"
        assert "Authorization" not in calls[0].headers
        assert [r["content"]["parts"][0]["text"] for r in body["requests"]] == ["first", "second"]
        assert all(r["outputDimensionality"] == EMBEDDING_DIMENSIONS for r in body["requests"])


@pytest.mark.parametrize("status", [408, 429, 500, 503])
def test_transient_status_retries_with_exponential_backoff(settings, status):
    calls, delays = [], []

    def handle(request):
        calls.append(request)
        return httpx.Response(status if len(calls) < 3 else 200, json=embedding_payload())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = HTTPEmbeddingProvider(provider_settings(settings), client, delays.append)
        assert len(provider.embed(["hello"])[0]) == EMBEDDING_DIMENSIONS
    assert len(calls) == 3 and delays == [1, 2]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_errors_are_not_retried_or_leaked(settings, status):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(status, text="private-provider-response test-only-key")

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError, match="^provider_request_rejected$"):
            HTTPEmbeddingProvider(provider_settings(settings), client).embed(["private document"])
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (httpx.ReadTimeout, ProviderTimeoutError),
        (httpx.ConnectError, ProviderError),
    ],
)
def test_network_failures_exhaust_bounded_retries(settings, exception, error):
    calls, delays = [], []

    def handle(request):
        calls.append(request)
        raise exception("must not leak", request=request)

    config = provider_settings(settings, provider_max_attempts=4, provider_max_backoff_seconds=2)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(error):
            HTTPEmbeddingProvider(config, client, delays.append).embed(["text"])
    assert len(calls) == 4 and delays == [1, 2, 2]


def test_rate_limit_exhaustion_is_sanitized(settings):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(429))) as client:
        with pytest.raises(ProviderError, match="^provider_temporarily_unavailable$"):
            HTTPEmbeddingProvider(provider_settings(settings), client, lambda _: None).embed(["x"])


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": []},
        embedding_payload([1.0]),
        embedding_payload(index=1),
        {"data": [{"index": 0, "embedding": [0.0] * EMBEDDING_DIMENSIONS}]},
        {"data": [{"index": 0, "embedding": [float("nan")] * EMBEDDING_DIMENSIONS}]},
        {"data": [{"index": False, "embedding": [1.0] * EMBEDDING_DIMENSIONS}]},
    ],
)
def test_malformed_embeddings_fail_without_retry(settings, payload):
    calls = []

    def handle(request):
        import json

        calls.append(request)
        return httpx.Response(200, content=json.dumps(payload))

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError, match="^invalid_embedding_response$"):
            HTTPEmbeddingProvider(provider_settings(settings), client).embed(["text"])
    assert len(calls) == 1


def test_non_json_embedding_response(settings):
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="html"))
    ) as c:
        with pytest.raises(ProviderError, match="invalid_embedding_response"):
            HTTPEmbeddingProvider(provider_settings(settings), c).embed(["text"])


@pytest.mark.parametrize(
    "values",
    [
        [],
        [1.0],
        [0.0] * EMBEDDING_DIMENSIONS,
        [float("nan")] * EMBEDDING_DIMENSIONS,
        [True] * EMBEDDING_DIMENSIONS,
    ],
)
def test_native_gemini_rejects_invalid_dimensions_values_and_zero_vectors(settings, values):
    import json

    response = httpx.Response(200, content=json.dumps({"embeddings": [{"values": values}]}))
    with httpx.Client(transport=httpx.MockTransport(lambda _: response)) as client:
        with pytest.raises(ProviderError, match="invalid_embedding_response"):
            HTTPEmbeddingProvider(
                provider_settings(settings, embedding_provider="gemini"), client
            ).embed(["x"])


def test_native_gemini_rejects_aggregated_or_missing_batch_items(settings):
    response = httpx.Response(200, json={"embeddings": [{"values": [1.0] * EMBEDDING_DIMENSIONS}]})
    with httpx.Client(transport=httpx.MockTransport(lambda _: response)) as client:
        with pytest.raises(ProviderError, match="invalid_embedding_response"):
            HTTPEmbeddingProvider(
                provider_settings(settings, embedding_provider="gemini"), client
            ).embed(["x", "y"])
