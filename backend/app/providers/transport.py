"""Shared bounded HTTP retries; neither request nor response bodies are logged."""

import time
from collections.abc import Callable, Mapping

import httpx
from pydantic import SecretStr

from app.deadlines import remaining_timeout
from app.errors import ProviderError, ProviderTimeoutError, RequestDeadlineError
from app.settings import Settings


def post_provider_json(
    client: httpx.Client,
    url: str,
    api_key: SecretStr,
    payload: Mapping[str, object],
    settings: Settings,
    sleep: Callable[[float], None] = time.sleep,
    *,
    api_key_header: bool = False,
) -> httpx.Response:
    """Retry transient HTTP failures with capped exponential backoff, then fail safely."""
    last_error: ProviderError = ProviderError("provider_unavailable")
    for attempt in range(settings.provider_max_attempts):
        try:
            response = client.post(
                url,
                headers={"x-goog-api-key": api_key.get_secret_value()}
                if api_key_header
                else {"Authorization": f"Bearer {api_key.get_secret_value()}"},
                json=dict(payload),
                timeout=remaining_timeout(settings.provider_timeout_seconds),
            )
        except httpx.TimeoutException:
            last_error = ProviderTimeoutError("provider_timeout")
        except httpx.TransportError:
            last_error = ProviderError("provider_unavailable")
        else:
            if response.is_success:
                return response
            if response.status_code not in (408, 429) and response.status_code < 500:
                raise ProviderError("provider_request_rejected")
            last_error = ProviderError("provider_temporarily_unavailable")
        if attempt + 1 < settings.provider_max_attempts:
            delay = min(
                settings.provider_backoff_seconds * 2**attempt,
                settings.provider_max_backoff_seconds,
            )
            if remaining_timeout(delay) < delay:
                raise RequestDeadlineError("request_deadline_exceeded")
            sleep(delay)
    raise last_error
