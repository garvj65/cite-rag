import hashlib
import json
import subprocess
from unittest.mock import Mock

import pytest
from app.answering.service import AnswerService
from app.errors import ProviderError
from app.providers.fakes import HashEmbeddingProvider, ScriptedLLMProvider
from app.retrieval.models import SearchHit, SearchResponse
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError

from eval import run, runtime, validate
from eval.engine import evaluate_questions
from eval.models import EvaluationOptions
from eval.schema import GoldenDataError, GoldenQuestion
from scripts import compare_strategies


def golden(tmp_path):
    # Offline CLI fixture only; never written to eval/golden.jsonl.
    path = tmp_path / "fixture.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "offline",
                "question": "Synthetic CLI fixture",
                "answerable": False,
                "gold_pages": [],
            }
        )
        + "\n"
    )
    return path


def sample_result(settings, options=None, failure=False):
    search = Mock()
    search.search.return_value = SearchResponse(
        strategy="hybrid", k=5, profile="fixture", score_type="rrf", results=[]
    )
    if failure:
        search.search.side_effect = ProviderError("private provider details")
    question = GoldenQuestion(
        id="offline", question="Synthetic CLI fixture", answerable=False, gold_pages=[]
    )
    return evaluate_questions(
        [question],
        search,
        AnswerService(settings, search, Mock()),
        options or EvaluationOptions(),
        {"mechanics_only": True},
    )


def test_validator_schema_and_valid_data_without_model_calls(tmp_path, capsys):
    assert validate.main(["--schema"]) == 0
    assert json.loads(capsys.readouterr().out)["additionalProperties"] is False
    assert validate.main(["--path", str(golden(tmp_path))]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["questions"] == output["unanswerable"] == 1
    assert output["answerable"] == 0
    assert len(output["golden_sha256"]) == 64


def test_invalid_or_empty_gold_fails_before_database_or_provider_setup(tmp_path, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("database must remain lazy"))
    monkeypatch.setattr(runtime, "create_db_engine", forbidden)
    monkeypatch.setattr(validate, "create_db_engine", forbidden)
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    assert validate.main(["--path", str(path), "--check-index"]) == 2
    assert run.main(["--golden", str(path)]) == 2
    assert compare_strategies.main(["--golden", str(path), "--chunk-sizes", "400"]) == 2
    forbidden.assert_not_called()


@pytest.mark.parametrize(
    "failure,code", [(GoldenDataError("private"), 2), (SQLAlchemyError("private"), 1)]
)
def test_index_validation_closes_database_and_sanitizes_errors(
    tmp_path, monkeypatch, capsys, failure, code
):
    engine = Mock()
    monkeypatch.setattr(validate, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(validate, "inspect_index", Mock(side_effect=failure))
    assert validate.main(["--path", str(golden(tmp_path)), "--check-index"]) == code
    engine.dispose.assert_called_once()
    assert "private" not in capsys.readouterr().err


@pytest.mark.parametrize("failure", [False, True])
def test_run_cli_persists_partial_results_and_marks_fake_mode(
    tmp_path, monkeypatch, settings, failure
):
    captured = []

    def evaluate(config, questions, digest, options):
        captured.append(config)
        return sample_result(settings, options, failure)

    monkeypatch.setattr(run, "run_evaluation", evaluate)
    output = tmp_path / "results"
    code = run.main(["--golden", str(golden(tmp_path)), "--fake", "--output", str(output)])
    assert code == int(failure)
    assert captured[0].embedding_provider == captured[0].llm_provider == "fake"
    assert not captured[0].enable_real_providers
    assert len(list(output.glob("*.jsonl"))) == 1


def test_focused_run_keeps_full_golden_digest_and_excludes_unselected_rows(
    tmp_path, monkeypatch, settings
):
    path = golden(tmp_path)
    with path.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "id": "other",
                    "question": "Another fixture",
                    "answerable": False,
                    "gold_pages": [],
                }
            )
            + "\n"
        )
    evaluate = Mock(return_value=sample_result(settings))
    monkeypatch.setattr(run, "run_evaluation", evaluate)
    output = tmp_path / "results"
    assert (
        run.main(["--golden", str(path), "--question-ids", "offline", "--output", str(output)]) == 0
    )
    _, questions, digest, _ = evaluate.call_args.args
    assert [question.id for question in questions] == ["offline"]
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    result = json.loads(next(output.glob("*.json")).read_text())
    assert result["metadata"]["selected_question_ids"] == ["offline"]
    assert "FOCUSED CHECK" in next(output.glob("*.md")).read_text()


@pytest.mark.parametrize("selection", ["", "unknown", "offline,offline", "offline,"])
def test_bad_focused_selection_fails_before_provider_or_database_setup(
    tmp_path, monkeypatch, selection
):
    evaluate = Mock(side_effect=AssertionError("must not start any evaluation"))
    monkeypatch.setattr(run, "run_evaluation", evaluate)
    assert run.main(["--golden", str(golden(tmp_path)), "--question-ids", selection]) == 2
    evaluate.assert_not_called()


@pytest.mark.parametrize(
    "error,expected",
    [(GoldenDataError("private"), 2), (SQLAlchemyError("private"), 1), (OSError("private"), 1)],
)
def test_run_cli_errors_are_clear_and_sanitized(tmp_path, monkeypatch, capsys, error, expected):
    monkeypatch.setattr(run, "run_evaluation", Mock(side_effect=error))
    assert run.main(["--golden", str(golden(tmp_path))]) == expected
    assert "private" not in capsys.readouterr().err


def test_runtime_preflight_and_provenance_exclude_secrets(settings, monkeypatch):
    engine, repository = Mock(), Mock()
    repository.has_profile.return_value = False
    monkeypatch.setattr(runtime, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(runtime, "PostgresSearchRepository", lambda _: repository)
    monkeypatch.setattr(runtime, "inspect_index", lambda *_: [{"doc_id": "a" * 64}])
    monkeypatch.setattr(runtime, "git_revision", lambda: "b" * 40)
    config = settings.model_copy(
        update={
            "gemini_api_key": SecretStr("never-save-this"),
            "database_url": SecretStr("never-save-db"),
            "embedding_provider": "fake",
            "llm_provider": "fake",
        }
    )
    question = GoldenQuestion(id="fixture", question="Synthetic", answerable=False, gold_pages=[])
    result = runtime.run_evaluation(config, [question], "a" * 64, EvaluationOptions())
    assert result.metadata["mechanics_only"] is True
    assert result.metadata["git_commit"] == "b" * 40
    assert "never-save" not in result.model_dump_json()
    assert "api_key" not in result.model_dump_json()
    engine.dispose.assert_called_once()


def test_runtime_preflight_rejects_bad_bounds_and_disposes_on_missing_index(settings, monkeypatch):
    factory = Mock()
    monkeypatch.setattr(runtime, "create_db_engine", factory)
    with pytest.raises(GoldenDataError):
        runtime.run_evaluation(settings, [], "hash", EvaluationOptions())
    with pytest.raises(GoldenDataError):
        runtime.run_evaluation(settings, [Mock()], "hash", EvaluationOptions(k=1000))
    factory.assert_not_called()
    monkeypatch.setattr(runtime, "inspect_index", Mock(side_effect=GoldenDataError("missing")))
    with pytest.raises(GoldenDataError):
        runtime.run_evaluation(settings, [Mock()], "hash", EvaluationOptions())
    factory.return_value.dispose.assert_called_once()


@pytest.mark.parametrize("returncode,expected", [(0, "abc"), (1, "unknown")])
def test_git_revision_is_local_only(monkeypatch, returncode, expected):
    result = Mock(returncode=returncode, stdout="abc\n")
    monkeypatch.setattr(runtime.subprocess, "run", Mock(return_value=result))
    assert runtime.git_revision() == expected


@pytest.mark.parametrize("error", [OSError(), subprocess.TimeoutExpired("git", 2)])
def test_revision_is_optional_outside_a_working_checkout(monkeypatch, error):
    monkeypatch.setattr(runtime.subprocess, "run", Mock(side_effect=error))
    assert runtime.git_revision() == "unknown"


@pytest.mark.parametrize(
    "stdout,code,expected", [("", 0, False), (" M eval/run.py", 0, True), ("", 1, None)]
)
def test_worktree_state_is_recorded_without_filenames(monkeypatch, stdout, code, expected):
    monkeypatch.setattr(
        runtime.subprocess, "run", Mock(return_value=Mock(stdout=stdout, returncode=code))
    )
    assert runtime.working_tree_dirty() is expected


@pytest.mark.parametrize("error", [OSError(), subprocess.TimeoutExpired("git", 2)])
def test_worktree_state_can_be_unknown(monkeypatch, error):
    monkeypatch.setattr(runtime.subprocess, "run", Mock(side_effect=error))
    assert runtime.working_tree_dirty() is None


@pytest.mark.parametrize("chat_mode,expected_calls", [("fake", 2), ("gemini", 1)])
def test_runtime_reuses_real_clients_and_resets_scripted_providers(
    settings, monkeypatch, chat_mode, expected_calls
):
    engine, repository = Mock(), Mock()
    repository.has_profile.return_value = True
    repository.vector_search.return_value = [
        SearchHit(
            doc_id="a" * 64,
            page=1,
            chunk_id=1,
            chunk_index=0,
            text="alpha beta",
            score=0.9,
            source="Offline",
            source_url=None,
            document_title="Fixture",
        )
    ]
    raw = json.dumps(
        {
            "answer": "Fixture answer",
            "supported": True,
            "citations": [{"doc_id": "a" * 64, "page": 1, "quote": "alpha beta"}],
        }
    )
    monkeypatch.setattr(runtime, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(runtime, "PostgresSearchRepository", lambda _: repository)
    monkeypatch.setattr(runtime, "inspect_index", lambda *_: [{"doc_id": "a" * 64}])
    embed = Mock(return_value=HashEmbeddingProvider())
    real_model = ScriptedLLMProvider([raw, raw])
    chat = Mock(
        side_effect=lambda *_: ScriptedLLMProvider([raw]) if chat_mode == "fake" else real_model
    )
    monkeypatch.setattr(runtime, "create_embedding_provider", embed)
    monkeypatch.setattr(runtime, "create_llm_provider", chat)
    config = settings.model_copy(update={"embedding_provider": "fake", "llm_provider": chat_mode})
    questions = [
        GoldenQuestion(
            id=str(i),
            question=f"Synthetic fixture {i}",
            answerable=True,
            gold_pages=[{"doc_id": "a" * 64, "page": 1}],
        )
        for i in range(2)
    ]
    result = runtime.run_evaluation(config, questions, "hash", EvaluationOptions(strategy="vector"))
    assert result.summary.errors == 0 and result.summary.citations_valid == 2
    assert embed.call_count == 1 and chat.call_count == expected_calls
    engine.dispose.assert_called_once()


def test_comparison_matrix_preserves_overlap_seed_and_identical_documents(
    tmp_path, monkeypatch, settings
):
    engine, runs, ingestions = Mock(), [], Mock()
    monkeypatch.setattr(compare_strategies, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(compare_strategies, "inspect_index", lambda *_: [{"doc_id": "a" * 64}])
    monkeypatch.setattr(compare_strategies, "ingest_profile", ingestions)

    def evaluate(config, questions, digest, options):
        runs.append((config, options))
        return sample_result(config, options)

    monkeypatch.setattr(compare_strategies, "run_evaluation", evaluate)
    output = tmp_path / "results"
    assert (
        compare_strategies.main(
            [
                "--golden",
                str(golden(tmp_path)),
                "--fake",
                "--chunk-sizes",
                "200",
                "400",
                "400",
                "--strategies",
                "vector",
                "keyword",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert len(runs) == 4
    assert {config.chunk_overlap_words for config, _ in runs} == {80}
    assert {option.seed for _, option in runs} == {42}
    assert all(config.llm_provider == config.embedding_provider == "fake" for config, _ in runs)
    ingestions.assert_not_called()
    assert "MECHANICS ONLY" in next(output.glob("*comparison.md")).read_text()
    engine.dispose.assert_called_once()


def test_comparison_rejects_different_document_sets_before_running(tmp_path, monkeypatch):
    monkeypatch.setattr(compare_strategies, "create_db_engine", lambda _: Mock())
    monkeypatch.setattr(
        compare_strategies,
        "inspect_index",
        Mock(side_effect=[[{"doc_id": "a" * 64}], [{"doc_id": "b" * 64}]]),
    )
    runner = Mock()
    monkeypatch.setattr(compare_strategies, "run_evaluation", runner)
    assert (
        compare_strategies.main(["--golden", str(golden(tmp_path)), "--chunk-sizes", "200", "400"])
        == 2
    )
    runner.assert_not_called()


@pytest.mark.parametrize(
    "error,code",
    [(GoldenDataError(), 2), (SQLAlchemyError(), 1), (ProviderError(), 1), (OSError(), 1)],
)
def test_comparison_ingestion_errors_are_handled(tmp_path, monkeypatch, error, code):
    monkeypatch.setattr(compare_strategies, "ingest_profile", Mock(side_effect=error))
    assert (
        compare_strategies.main(
            ["--golden", str(golden(tmp_path)), "--chunk-sizes", "400", "--ingest"]
        )
        == code
    )


def test_comparison_validates_overlap_and_retrieval_bounds_before_ingesting(tmp_path, monkeypatch):
    ingest = Mock()
    monkeypatch.setattr(compare_strategies, "ingest_profile", ingest)
    for bounds in (["--chunk-sizes", "20"], ["--chunk-sizes", "400", "--k", "1000"]):
        assert (
            compare_strategies.main(["--golden", str(golden(tmp_path)), "--ingest", *bounds]) == 2
        )
    ingest.assert_not_called()


def test_retrieval_only_cli_flag_is_explicit_and_persisted(tmp_path, monkeypatch, settings):
    captured = []

    def evaluate(config, questions, digest, options):
        captured.append(options)
        return sample_result(settings, options)

    monkeypatch.setattr(run, "run_evaluation", evaluate)
    output = tmp_path / "results"
    assert (
        run.main(["--golden", str(golden(tmp_path)), "--retrieval-only", "--output", str(output)])
        == 0
    )
    assert captured[0].retrieval_only is True
    data = json.loads(next(output.glob("*.json")).read_text())
    assert data["options"]["retrieval_only"] is True
    assert data["summary"]["refusal_accuracy"] is None


def test_retrieval_only_runtime_does_not_initialize_chat_or_taint_real_ranking_label(
    settings, monkeypatch
):
    engine, repository = Mock(), Mock()
    repository.has_profile.return_value = False
    monkeypatch.setattr(runtime, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(runtime, "PostgresSearchRepository", lambda _: repository)
    monkeypatch.setattr(runtime, "inspect_index", lambda *_: [{"doc_id": "a" * 64}])
    forbidden = Mock(side_effect=AssertionError("chat must remain lazy"))
    monkeypatch.setattr(runtime, "create_llm_provider", forbidden)
    config = settings.model_copy(update={"embedding_provider": "gemini", "llm_provider": "fake"})
    question = GoldenQuestion(id="offline", question="Synthetic", answerable=False, gold_pages=[])
    result = runtime.run_evaluation(
        config, [question], "hash", EvaluationOptions(retrieval_only=True)
    )
    forbidden.assert_not_called()
    assert result.metadata["mechanics_only"] is False
    assert result.summary.refusal_accuracy is None
    engine.dispose.assert_called_once()
