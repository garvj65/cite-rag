import json
from unittest.mock import Mock

import pytest
from app.answering.service import AnswerService
from app.errors import (
    ModelOutputError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
)
from app.providers.fakes import ScriptedLLMProvider
from app.retrieval.models import SearchHit, SearchResponse
from app.retrieval.service import SearchService
from sqlalchemy.exc import SQLAlchemyError

from eval.engine import evaluate_questions
from eval.models import EvaluationOptions
from eval.report import atomic_write, render_report, write_report
from eval.schema import GoldenQuestion


def question(answerable=True):
    return GoldenQuestion(
        id="positive" if answerable else "negative",
        question="Synthetic positive" if answerable else "Synthetic negative",
        answerable=answerable,
        gold_pages=[{"doc_id": "a" * 64, "page": 1}] if answerable else [],
    )


def retrieval(empty=False):
    return SearchResponse(
        strategy="vector",
        k=5,
        profile="fixture",
        score_type="cosine_similarity",
        results=[]
        if empty
        else [
            SearchHit(
                doc_id="a" * 64,
                page=1,
                chunk_id=1,
                chunk_index=0,
                score=0.9,
                text="Original fixture evidence.",
                document_title="Offline fixture",
                source="Test",
                source_url=None,
            )
        ],
    )


def evaluate(settings, raw=None):
    search = Mock(spec=SearchService)
    search.search.side_effect = lambda query, *_: retrieval(empty=query.endswith("negative"))
    payload = raw or json.dumps(
        {
            "answer": "Fixture answer.",
            "supported": True,
            "citations": [{"doc_id": "a" * 64, "page": 1, "quote": "Original fixture evidence."}],
        }
    )
    model = ScriptedLLMProvider([payload])
    service = AnswerService(settings, search, lambda: model)
    times = iter([0.0, 0.002, 0.005, 0.01, 0.013, 0.020])
    result = evaluate_questions(
        [question(), question(False)],
        search,
        service,
        EvaluationOptions(strategy="vector"),
        {"mechanics_only": True},
        lambda: next(times),
    )
    return result, search, model


def test_one_retrieval_per_question_correct_denominators_and_seeded_order(settings):
    result, search, model = evaluate(settings)
    assert search.search.call_count == 2 and len(model.calls) == 1
    assert [row.id for row in result.rows] == ["negative", "positive"]
    assert [row.id for row in evaluate(settings)[0].rows] == [row.id for row in result.rows]
    summary = result.summary
    assert summary.questions == 2 and summary.answerable == summary.unanswerable == 1
    assert (
        summary.recall_at_k
        == summary.mrr
        == summary.citation_validity
        == summary.refusal_accuracy
        == 1
    )
    assert summary.errors == 0 and summary.citations_proposed == summary.citations_valid == 1
    assert summary.latency_p50_ms == pytest.approx(7.5)
    assert summary.latency_p95_ms == pytest.approx(9.75)
    assert "Original fixture evidence." not in json.dumps(result.rows[1].retrieved[0].model_dump())


def test_invalid_citations_are_measured_before_answer_refusal(settings):
    raw = json.dumps(
        {
            "answer": "Fixture answer.",
            "supported": True,
            "citations": [
                {"doc_id": "a" * 64, "page": 1, "quote": "Original fixture evidence."},
                {"doc_id": "a" * 64, "page": 1, "quote": "invented"},
            ],
        }
    )
    result, _, _ = evaluate(settings, raw)
    assert result.summary.citation_validity == 0.5
    assert result.summary.citations_proposed == 2
    assert result.rows[1].answer.citations == []
    assert not result.rows[1].answer.supported


@pytest.mark.parametrize(
    "failure,code",
    [
        (ProviderTimeoutError("private details"), "provider_timeout"),
        (ProviderConfigurationError("private details"), "provider_not_configured"),
        (ProviderError("private details"), "provider_failure"),
        (ModelOutputError("private details"), "invalid_model_output"),
        (SQLAlchemyError("private details"), "database_unavailable"),
    ],
)
def test_retrieval_failures_score_zero_without_becoming_refusals(settings, failure, code):
    search, answers = Mock(), Mock()
    search.search.side_effect = failure
    result = evaluate_questions(
        [question(), question(False)], search, answers, EvaluationOptions(), {}
    )
    assert result.summary.errors == 2 and result.summary.refusal_accuracy == 0
    assert result.summary.recall_at_k == result.summary.mrr == 0
    assert result.summary.citation_validity is None
    assert result.rows[0].error == code and result.rows[0].answer is None
    assert "private details" not in result.model_dump_json()
    answers.answer_from_retrieval.assert_not_called()


def test_generation_failure_preserves_retrieval_measurement(settings):
    search, answers = Mock(), Mock()
    search.search.return_value = retrieval()
    answers.answer_from_retrieval.side_effect = ProviderError("private")
    result = evaluate_questions([question()], search, answers, EvaluationOptions(), {})
    assert result.summary.recall_at_k == result.summary.mrr == 1
    assert result.summary.errors == 1 and result.summary.refusal_accuracy is None


def test_empty_question_set_cannot_produce_an_evaluation():
    with pytest.raises(ValueError):
        evaluate_questions([], Mock(), Mock(), EvaluationOptions(), {})


def test_pacing_occurs_between_questions_and_is_excluded_from_latency():
    elapsed = 0.0
    pauses = []

    def clock():
        nonlocal elapsed
        elapsed += 0.001
        return elapsed

    def pause(seconds):
        nonlocal elapsed
        pauses.append(seconds)
        elapsed += seconds

    search, answers = Mock(), Mock()
    search.search.return_value = retrieval(empty=True)
    answers.answer_from_retrieval.return_value = None
    result = evaluate_questions(
        [question(), question(False)],
        search,
        answers,
        EvaluationOptions(question_delay_seconds=15),
        {},
        clock,
        pause,
    )
    assert pauses == [15]
    assert [row.latency_ms for row in result.rows] == pytest.approx([2, 2])
    assert [row.retrieval_latency_ms for row in result.rows] == pytest.approx([1, 1])


def test_reports_label_mechanics_and_write_raw_records(settings, tmp_path):
    result, _, _ = evaluate(settings)
    path = write_report(result, tmp_path)
    text = path.read_text()
    assert "MECHANICS ONLY" in text and "No LLM judge" in text and "not bit-for-bit" in text
    assert "1 valid / 1 proposed" in text
    assert len(path.with_suffix(".jsonl").read_text().splitlines()) == 2
    assert json.loads(path.with_suffix(".json").read_text())["summary"]["errors"] == 0
    assert len(list(tmp_path.glob("*.md"))) == 1
    result.metadata = {}
    result.summary.citation_validity = None
    assert "Configured-provider evaluation" in render_report(result)
    assert "N/A" in render_report(result)


def test_atomic_report_failure_preserves_existing_output(tmp_path, monkeypatch):
    path = tmp_path / "report.md"
    path.write_text("existing")

    def fail(*_):
        raise OSError("disk failure")

    monkeypatch.setattr("eval.report.os.replace", fail)
    with pytest.raises(OSError):
        atomic_write(path, "new")
    assert path.read_text() == "existing"
    assert list(tmp_path.iterdir()) == [path]
