import hashlib
import json

import pytest
from app.db.repository import PostgresIngestionRepository
from app.ingestion.service import IngestionService, indexing_profile
from app.providers.fakes import HashEmbeddingProvider
from pydantic import SecretStr

from eval import run, validate
from eval.models import EvaluationOptions
from eval.runtime import inspect_index, run_evaluation
from eval.schema import GoldenDataError, GoldenQuestion
from scripts import compare_strategies

pytestmark = pytest.mark.integration


def fixture_config(settings, engine, doc_id):
    return settings.model_copy(
        update={
            "database_url": SecretStr(engine.url.render_as_string(hide_password=False)),
            "embedding_provider": "fake",
            "llm_provider": "fake",
            "enable_real_providers": False,
            "fake_llm_response": json.dumps(
                {
                    "answer": "Offline fixture answer.",
                    "supported": True,
                    "citations": [{"doc_id": doc_id, "page": 1, "quote": "alpha beta"}],
                }
            ),
        }
    )


@pytest.mark.parametrize("strategy", ["vector", "keyword", "hybrid"])
def test_complete_evaluation_uses_real_postgres_and_scripted_answers(
    engine, settings, pdf_path, strategy
):
    doc_id = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    config = fixture_config(settings, engine, doc_id)
    IngestionService(config, HashEmbeddingProvider(), PostgresIngestionRepository(engine)).ingest(
        pdf_path
    )
    questions = [
        GoldenQuestion(
            id="offline-answerable",
            question="alpha beta",
            answerable=True,
            gold_pages=[{"doc_id": doc_id, "page": 1}],
        ),
        GoldenQuestion(
            id="offline-negative",
            question="nonexistentfixtureword",
            answerable=False,
            gold_pages=[],
        ),
    ]
    result = run_evaluation(config, questions, "a" * 64, EvaluationOptions(strategy=strategy))
    assert result.summary.recall_at_k == result.summary.mrr == 1
    assert result.summary.citation_validity == result.summary.refusal_accuracy == 1
    assert result.summary.errors == 0
    assert result.metadata["corpus"][0]["doc_id"] == doc_id
    assert result.metadata["mechanics_only"] is True


def test_empty_or_mislabeled_index_is_rejected_before_evaluation(engine, settings, pdf_path):
    doc_id = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    config = fixture_config(settings, engine, doc_id)
    gold = GoldenQuestion(
        id="fixture", question="alpha", answerable=True, gold_pages=[{"doc_id": doc_id, "page": 99}]
    )
    with pytest.raises(GoldenDataError, match="No chunks"):
        inspect_index(engine, indexing_profile(config), [gold])
    IngestionService(config, HashEmbeddingProvider(), PostgresIngestionRepository(engine)).ingest(
        pdf_path
    )
    with pytest.raises(GoldenDataError, match="Some gold"):
        inspect_index(engine, indexing_profile(config), [gold])


def test_cli_and_chunk_comparison_with_disposable_fixture_only(
    engine, settings, pdf_path, tmp_path, monkeypatch
):
    doc_id = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    config = fixture_config(settings, engine, doc_id)
    for name, value in {
        "DATABASE_URL": config.database_url.get_secret_value(),
        "EMBEDDING_PROVIDER": "fake",
        "LLM_PROVIDER": "fake",
        "FAKE_LLM_RESPONSE": config.fake_llm_response,
        "CHUNK_SIZE_WORDS": "5",
        "CHUNK_OVERLAP_WORDS": "1",
    }.items():
        monkeypatch.setenv(name, value)
    golden = tmp_path / "offline-fixture.jsonl"
    golden.write_text(
        json.dumps(
            {
                "id": "offline",
                "question": "alpha beta",
                "answerable": True,
                "gold_pages": [{"doc_id": doc_id, "page": 1}],
            }
        )
        + "\n"
    )
    output = tmp_path / "results"
    assert (
        compare_strategies.main(
            [
                "--golden",
                str(golden),
                "--chunk-sizes",
                "3",
                "5",
                "--overlap",
                "1",
                "--fake",
                "--ingest",
                "--corpus",
                str(tmp_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    comparison = next(output.glob("*comparison.md")).read_text()
    assert "MECHANICS ONLY" in comparison
    assert len(list(output.glob("*.json"))) == 6
    for path in output.glob("*.json"):
        summary = json.loads(path.read_text())["summary"]
        assert summary["recall_at_k"] == summary["mrr"] == summary["citation_validity"] == 1
        assert summary["refusal_accuracy"] is None
    assert validate.main(["--path", str(golden), "--check-index"]) == 0
    assert (
        run.main(["--golden", str(golden), "--strategy", "keyword", "--output", str(output)]) == 0
    )
