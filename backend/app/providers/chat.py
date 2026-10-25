"""Structured JSON generation through an explicitly selected OpenAI-compatible endpoint."""

import time
from collections.abc import Callable

import httpx
from pydantic import BaseModel, ValidationError

from app.answering.models import ModelAnswer
from app.errors import ModelOutputError, ProviderConfigurationError, ProviderError
from app.providers.transport import post_provider_json
from app.settings import Settings


class _Message(BaseModel):
    content: str | None = None
    refusal: str | None = None


class _Choice(BaseModel):
    message: _Message
    finish_reason: str


class _Completion(BaseModel):
    choices: list[_Choice]


class HTTPChatProvider:
    """Request the exact answer schema and reject truncated or malformed provider wrappers."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not settings.enable_real_providers or settings.llm_provider == "fake":
            raise ProviderConfigurationError("real_chat_provider_not_enabled")
        self._settings, self._client, self._sleep = settings, client, sleep
        if settings.llm_provider == "gemini":
            self._base = "https://generativelanguage.googleapis.com/v1beta/openai"
            self._key, self._model = settings.gemini_api_key, settings.gemini_chat_model
        else:
            self._base = "https://api.openai.com/v1"
            self._key, self._model = settings.openai_api_key, settings.openai_chat_model
        if not self._key.get_secret_value().strip() or not self._model.strip():
            raise ProviderConfigurationError("missing_chat_provider_configuration")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate schema-constrained text; evidence validation remains in the application."""
        response = post_provider_json(
            self._client,
            f"{self._base}/chat/completions",
            self._key,
            {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "citerag_answer",
                        "strict": True,
                        "schema": ModelAnswer.model_json_schema(),
                    },
                },
                "max_completion_tokens": self._settings.chat_max_completion_tokens,
            },
            self._settings,
            self._sleep,
        )
        try:
            completion = _Completion.model_validate_json(response.content)
        except ValidationError:
            raise ModelOutputError("invalid_chat_response") from None
        if len(completion.choices) != 1:
            raise ModelOutputError("invalid_chat_response")
        choice = completion.choices[0]
        if choice.message.refusal:
            raise ProviderError("chat_provider_refused_request")
        if choice.finish_reason != "stop" or not choice.message.content:
            raise ModelOutputError("incomplete_chat_response")
        return choice.message.content
