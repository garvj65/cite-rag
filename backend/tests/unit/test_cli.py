import json
from unittest.mock import Mock

from app.ingest import main
from sqlalchemy.exc import OperationalError


def configure_offline_cli(monkeypatch, settings, repository):
    monkeypatch.setattr("app.ingest.Settings", lambda: settings)
    monkeypatch.setattr("app.ingest.PostgresIngestionRepository", lambda _: repository)


def test_cli_path_validation_and_empty_directory(tmp_path, capsys):
    assert main(["--path", str(tmp_path / "absent")]) == 2
    other = tmp_path / "file.txt"
    other.write_text("text")
    assert main(["--path", str(other)]) == 2
    assert main(["--path", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["docs"] == 0


def test_cli_ingestion_progress_summary_duplicate(
    settings, repository, pdf_path, monkeypatch, capsys
):
    configure_offline_cli(monkeypatch, settings, repository)
    assert main(["--path", str(pdf_path), "--fake"]) == 0
    output = capsys.readouterr()
    summary = json.loads(output.out)
    assert (summary["docs"], summary["pages"], summary["chunks"]) == (1, 2, 3)
    assert "[1/1]" in output.err and "alpha beta" not in output.err
    assert main(["--path", str(pdf_path.parent), "--fake"]) == 0
    assert json.loads(capsys.readouterr().out)["skipped"] == 1


def test_cli_provider_disabled_does_not_contact_network(
    settings, repository, pdf_path, monkeypatch, capsys
):
    configure_offline_cli(monkeypatch, settings, repository)
    assert main(["--path", str(pdf_path)]) == 2
    assert "enable real providers" in capsys.readouterr().err


def test_cli_real_provider_contract_uses_mock_transport(
    settings, repository, pdf_path, monkeypatch, capsys
):
    import httpx
    from pydantic import SecretStr

    enabled = settings.model_copy(
        update={
            "enable_real_providers": True,
            "gemini_api_key": SecretStr("test-only-key"),
        }
    )
    configure_offline_cli(monkeypatch, enabled, repository)

    def handle(request):
        texts = json.loads(request.content)["requests"]
        return httpx.Response(
            200,
            json={"embeddings": [{"values": [1.0] * 1536} for _ in texts]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr("app.providers.factory.httpx.Client", lambda: client)
    assert main(["--path", str(pdf_path)]) == 0
    assert json.loads(capsys.readouterr().out)["docs"] == 1


def test_cli_db_error_is_sanitized(settings, repository, pdf_path, monkeypatch, capsys):
    configure_offline_cli(monkeypatch, settings, repository)
    monkeypatch.setattr(
        repository,
        "contains",
        Mock(
            side_effect=OperationalError(
                "secret-password document-text", {}, Exception("private database message")
            )
        ),
    )
    assert main(["--path", str(pdf_path), "--fake"]) == 1
    error = capsys.readouterr().err
    assert "Database unavailable" in error and "secret-password" not in error


def test_cli_invalid_manifest(tmp_path, pdf_path, monkeypatch, capsys):
    (tmp_path / "manifest.yaml").write_text("documents: wrong-type")
    assert main(["--path", str(pdf_path), "--fake"]) == 2
    assert "Invalid settings or corpus manifest" in capsys.readouterr().err
