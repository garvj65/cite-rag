"""Select one explicit provider without creating clients for keyword search."""

from contextlib import ExitStack

import httpx
from pydantic import SecretStr

from app.errors import ProviderConfigurationError
from app.providers.chat import HTTPChatProvider
from app.providers.fakes import HashEmbeddingProvider, ScriptedLLMProvider
from app.providers.http import HTTPEmbeddingProvider
from app.providers.interfaces import EmbeddingProvider, LLMProvider
from app.settings import Settings


def _require_configuration(enabled: bool, key: SecretStr, model: str) -> None:
    if not enabled:
        raise ProviderConfigurationError("real_providers_disabled")
    if not key.get_secret_value().strip() or not model.strip():
        raise ProviderConfigurationError("missing_provider_configuration")


def configured_model_id(settings: Settings) -> str:
    """Return indexing identity without credentials, HTTP clients, or API calls."""
    if settings.embedding_provider == "fake":
        return HashEmbeddingProvider().model_id
    model = (
        settings.gemini_embedding_model
        if settings.embedding_provider == "gemini"
        else settings.openai_embedding_model
    )
    return f"{settings.embedding_provider}/{model}"


def create_embedding_provider(settings: Settings, stack: ExitStack) -> EmbeddingProvider:
    """Create the configured provider and register HTTP cleanup in the caller's scope."""
    if settings.embedding_provider == "fake":
        return HashEmbeddingProvider()
    _require_configuration(
        settings.enable_real_providers,
        settings.gemini_api_key
        if settings.embedding_provider == "gemini"
        else settings.openai_api_key,
        settings.gemini_embedding_model
        if settings.embedding_provider == "gemini"
        else settings.openai_embedding_model,
    )
    client = stack.enter_context(httpx.Client())
    return HTTPEmbeddingProvider(settings, client)


def create_llm_provider(settings: Settings, stack: ExitStack) -> LLMProvider:
    """Create an explicit real adapter or one clearly labeled, per-request scripted response."""
    if settings.llm_provider == "fake":
        return ScriptedLLMProvider([settings.fake_llm_response])
    _require_configuration(
        settings.enable_real_providers,
        settings.gemini_api_key if settings.llm_provider == "gemini" else settings.openai_api_key,
        settings.gemini_chat_model
        if settings.llm_provider == "gemini"
        else settings.openai_chat_model,
    )
    return HTTPChatProvider(settings, stack.enter_context(httpx.Client()))
