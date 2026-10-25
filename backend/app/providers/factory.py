"""Select one explicit provider without creating clients for keyword search."""

from contextlib import ExitStack

import httpx

from app.errors import ProviderConfigurationError
from app.providers.fakes import HashEmbeddingProvider
from app.providers.http import HTTPEmbeddingProvider
from app.providers.interfaces import EmbeddingProvider
from app.settings import Settings


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
    if not settings.enable_real_providers:
        raise ProviderConfigurationError("real_providers_disabled")
    client = stack.enter_context(httpx.Client())
    return HTTPEmbeddingProvider(settings, client)
