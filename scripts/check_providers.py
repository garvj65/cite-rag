"""Explicit, small provider connectivity checks with allowlisted diagnostics only."""

import argparse
import json
from collections.abc import Sequence

import httpx
from app.answering.models import ModelAnswer
from app.errors import (
    ModelOutputError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
)
from app.providers.chat import HTTPChatProvider
from app.providers.http import HTTPEmbeddingProvider
from app.settings import Settings
from pydantic import ValidationError

SAFE_STATUSES = {
    "INVALID_ARGUMENT",
    "UNAUTHENTICATED",
    "PERMISSION_DENIED",
    "NOT_FOUND",
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "INTERNAL",
    "DEADLINE_EXCEEDED",
}
SAFE_REASONS = {
    "API_KEY_INVALID",
    "API_KEY_SERVICE_BLOCKED",
    "API_KEY_HTTP_REFERRER_BLOCKED",
    "API_KEY_IP_ADDRESS_BLOCKED",
    "SERVICE_DISABLED",
    "BILLING_DISABLED",
    "RATE_LIMIT_EXCEEDED",
    "QUOTA_EXCEEDED",
    "CONSUMER_INVALID",
    "invalid_api_key",
    "model_not_found",
    "insufficient_quota",
    "rate_limit_exceeded",
}


def response_diagnostic(response: httpx.Response) -> dict[str, object]:
    """Copy numeric HTTP status and known error codes, excluding headers/body messages."""
    result: dict[str, object] = {"http_status": response.status_code}
    try:
        payload = response.json()
    except ValueError:
        return result
    if response.is_success:
        if isinstance(payload, dict):
            rows = payload.get("embeddings", payload.get("data"))
            if isinstance(rows, list):
                result["embedding_rows"] = len(rows)
                result["embedding_dimensions"] = [
                    len(vector) if isinstance(vector, list) else 0
                    for row in rows
                    for vector in [
                        row.get("values", row.get("embedding")) if isinstance(row, dict) else None
                    ]
                ]
        return result
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return result
    status = error.get("status")
    if isinstance(status, str) and status in SAFE_STATUSES:
        result["provider_status"] = status
    candidates = [error.get("code")]
    details = error.get("details")
    if isinstance(details, list):
        candidates.extend(item.get("reason") for item in details if isinstance(item, dict))
    result["reason_codes"] = sorted(
        {x for x in candidates if isinstance(x, str) and x in SAFE_REASONS}
    )
    return result


def check_providers(
    settings: Settings,
    transport: httpx.BaseTransport | None = None,
    *,
    embedding_only: bool = False,
) -> list[dict[str, object]]:
    """Check one tiny embedding batch and optionally chat, without printing content."""
    reports: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []

    def capture(response: httpx.Response) -> None:
        response.read()
        attempts.append(response_diagnostic(response))

    with httpx.Client(transport=transport, event_hooks={"response": [capture]}) as client:
        for component in ("embedding",) if embedding_only else ("embedding", "chat"):
            attempts = []
            report: dict[str, object] = {"component": component, "ok": False}
            try:
                if component == "embedding":
                    HTTPEmbeddingProvider(settings, client).embed(["CiteRAG connectivity check."])
                else:
                    text = HTTPChatProvider(settings, client).generate(
                        "Return only JSON matching the required schema.",
                        'Return answer="", citations=[], supported=false.',
                    )
                    ModelAnswer.model_validate_json(text)
            except ProviderConfigurationError:
                report["error"] = "provider_not_configured"
            except ProviderTimeoutError:
                report["error"] = "provider_timeout"
            except (ModelOutputError, ValidationError):
                report["error"] = "invalid_model_output"
            except ProviderError:
                report["error"] = "provider_failure"
            else:
                report["ok"] = True
            report["http_attempts"] = attempts
            reports.append(report)
    return reports


def main(argv: Sequence[str] | None = None) -> int:
    """Require explicit real-call opt-in and return only sanitized diagnostic JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-real-calls", action="store_true")
    parser.add_argument("--embedding-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        settings = Settings()
    except ValidationError:
        print('{"error":"invalid_settings"}')
        return 2
    if not args.allow_real_calls or not settings.enable_real_providers:
        print('{"error":"real_calls_not_authorized"}')
        return 2
    reports = (
        check_providers(settings, embedding_only=True)
        if args.embedding_only
        else check_providers(settings)
    )
    print(json.dumps({"checks": reports}))
    return 0 if all(report["ok"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
