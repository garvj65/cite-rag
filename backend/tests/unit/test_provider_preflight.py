import json
from unittest.mock import Mock

import httpx
import pytest
from app.settings import EMBEDDING_DIMENSIONS
from pydantic import SecretStr

from scripts import check_providers


def test_status_diagnostics_never_copy_key_messages_headers_or_unknown_codes():
    response = httpx.Response(
        400,
        json={
            "error": {
                "status": "INVALID_ARGUMENT",
                "message": "secret-key-private-text",
                "code": "secret-key-private-text",
                "details": [
                    {"reason": "API_KEY_INVALID", "metadata": {"key": "secret-key-private-text"}},
                    {"reason": "secret-key-private-text"},
                    None,
                ],
            }
        },
        headers={"private": "secret-key-private-text"},
    )
    assert check_providers.response_diagnostic(response) == {
        "http_status": 400,
        "provider_status": "INVALID_ARGUMENT",
        "reason_codes": ["API_KEY_INVALID"],
    }
    for body in (b"<html>secret-key-private-text</html>", b"[]", b'{"error":null}'):
        assert check_providers.response_diagnostic(httpx.Response(502, content=body)) == {
            "http_status": 502
        }


@pytest.mark.parametrize("failure", [False, True])
def test_checks_use_mock_http_and_report_only_safe_metadata(settings, failure):
    config = settings.model_copy(
        update={
            "enable_real_providers": True,
            "embedding_provider": "gemini",
            "llm_provider": "gemini",
            "gemini_api_key": SecretStr("private-key"),
        }
    )
    requests = []

    def handle(request):
        requests.append(request)
        if failure:
            return httpx.Response(
                404, json={"error": {"status": "NOT_FOUND", "message": "private-key"}}
            )
        if request.url.path.endswith(":batchEmbedContents"):
            return httpx.Response(
                200, json={"embeddings": [{"values": [1.0] * EMBEDDING_DIMENSIONS}]}
            )
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [{"text": '{"answer":"","citations":[],"supported":false}'}]
                        },
                    }
                ]
            },
        )

    reports = check_providers.check_providers(config, httpx.MockTransport(handle))
    assert len(requests) == 2
    assert [r["ok"] for r in reports] == [not failure, not failure]
    assert "private-key" not in json.dumps(reports)
    assert [r["component"] for r in reports] == ["embedding", "chat"]


def test_explicit_opt_in_is_required_before_any_http(settings, monkeypatch, capsys):
    forbidden = Mock(side_effect=AssertionError("must not call"))
    monkeypatch.setattr(check_providers, "Settings", lambda: settings)
    monkeypatch.setattr(check_providers, "check_providers", forbidden)
    assert check_providers.main([]) == 2
    assert check_providers.main(["--allow-real-calls"]) == 2
    forbidden.assert_not_called()
    assert "real_calls_not_authorized" in capsys.readouterr().out


def test_cli_exit_status_and_safe_json(settings, monkeypatch, capsys):
    config = settings.model_copy(update={"enable_real_providers": True})
    monkeypatch.setattr(check_providers, "Settings", lambda: config)
    monkeypatch.setattr(
        check_providers, "check_providers", lambda _: [{"component": "embedding", "ok": False}]
    )
    assert check_providers.main(["--allow-real-calls"]) == 1
    assert json.loads(capsys.readouterr().out)["checks"][0]["ok"] is False


def test_success_diagnostics_report_shapes_without_embedding_values():
    response = httpx.Response(
        200, json={"embeddings": [{"values": [0.1, 0.2]}], "private": "never print"}
    )
    assert check_providers.response_diagnostic(response) == {
        "http_status": 200,
        "embedding_rows": 1,
        "embedding_dimensions": [2],
    }
