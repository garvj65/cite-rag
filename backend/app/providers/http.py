"""Native Gemini batch embeddings and the explicitly selected OpenAI adapter."""

import time
from collections.abc import Callable, Sequence
from typing import Annotated

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.errors import ProviderConfigurationError, ProviderError
from app.providers.pacing import get_pacer
from app.providers.transport import post_provider_json
from app.settings import EMBEDDING_DIMENSIONS, Settings


class _EmbeddingItem(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    index: Annotated[int, Field(strict=True, ge=0)]
    embedding: list[Annotated[float, Field(strict=True)]]


class _EmbeddingResponse(BaseModel):
    data: list[_EmbeddingItem]


class _GeminiEmbeddingItem(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    values: list[Annotated[float, Field(strict=True)]]


class _GeminiEmbeddingResponse(BaseModel):
    embeddings: list[_GeminiEmbeddingItem]


class HTTPEmbeddingProvider:
    """Call one selected provider with validated output and bounded retries."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._client = client
        self._sleep = sleep
        if not settings.enable_real_providers:
            raise ProviderConfigurationError("real_providers_disabled")
        if settings.embedding_provider == "fake":
            raise ProviderConfigurationError("fake_provider_requires_factory")
        if settings.embedding_provider == "gemini":
            self._base = "https://generativelanguage.googleapis.com/v1beta"
            self._key = settings.gemini_api_key
            self._model = settings.gemini_embedding_model
        else:
            self._base = "https://api.openai.com/v1"
            self._key = settings.openai_api_key
            self._model = settings.openai_embedding_model
        if not self._key.get_secret_value().strip():
            raise ProviderConfigurationError("missing_provider_api_key")

    @property
    def model_id(self) -> str:
        """Identify the selected provider and model for reproducible indexing."""
        return f"{self._settings.embedding_provider}/{self._model}"

    @property
    def dimensions(self) -> int:
        """Return the shared database embedding dimension."""
        return EMBEDDING_DIMENSIONS

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch; retry connection errors, timeouts, rate limits, and 5xx."""
        if not texts:
            return []
        if self._settings.embedding_provider == "gemini":
            endpoint = f"{self._base}/models/{self._model}:batchEmbedContents"
            response = post_provider_json(
                self._client,
                endpoint,
                self._key,
                {
                    "requests": [
                        {
                            "model": f"models/{self._model}",
                            "content": {"parts": [{"text": text}]},
                            "outputDimensionality": self.dimensions,
                        }
                        for text in texts
                    ]
                },
                self._settings,
                self._sleep,
                api_key_header=True,
                pacer=get_pacer(endpoint, self._settings.gemini_embedding_inputs_per_minute),
                request_units=len(texts),
            )
            try:
                parsed = _GeminiEmbeddingResponse.model_validate_json(response.content)
            except ValidationError:
                raise ProviderError("invalid_embedding_response") from None
            vectors = [item.values for item in parsed.embeddings]
            if len(vectors) != len(texts) or any(
                len(vector) != self.dimensions or not any(vector) for vector in vectors
            ):
                raise ProviderError("invalid_embedding_response")
            return vectors
        response = post_provider_json(
            self._client,
            f"{self._base}/embeddings",
            self._key,
            {"model": self._model, "input": list(texts), "dimensions": self.dimensions},
            self._settings,
            self._sleep,
        )
        return self._parse(response, len(texts))

    def _parse(self, response: httpx.Response, count: int) -> list[list[float]]:
        try:
            parsed = _EmbeddingResponse.model_validate_json(response.content)
        except ValidationError:
            raise ProviderError("invalid_embedding_response") from None
        items = sorted(parsed.data, key=lambda item: item.index)
        if [item.index for item in items] != list(range(count)):
            raise ProviderError("invalid_embedding_response")
        vectors = [item.embedding for item in items]
        if any(len(vector) != self.dimensions or not any(vector) for vector in vectors):
            raise ProviderError("invalid_embedding_response")
        return vectors
