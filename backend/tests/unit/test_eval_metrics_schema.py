import hashlib
import json
from pathlib import Path

import pytest

from eval.metrics import (
    citation_validity,
    percentile,
    recall_at_k,
    reciprocal_rank,
    refusal_accuracy,
)
from eval.schema import GoldenDataError, GoldenQuestion, GoldPage, load_golden


def page(number, doc_id="a" * 64):
    return GoldPage(doc_id=doc_id, page=number)


def row(**updates):
    # Synthetic schema fixture, never a corpus question or user golden answer.
    return {
        "id": "fixture-1",
        "question": "Synthetic schema fixture",
        "answerable": True,
        "gold_pages": [{"doc_id": "a" * 64, "page": 1}],
        **updates,
    }


def test_hand_computed_page_recall_and_chunk_rank_with_duplicates():
    gold = [page(1), page(2)]
    retrieved = [page(9), page(1), page(1), page(2)]
    assert recall_at_k(gold, retrieved, 3) == 0.5
    assert recall_at_k(gold, retrieved, 4) == 1.0
    assert reciprocal_rank(gold, retrieved, 4) == 0.5
    assert recall_at_k(gold, retrieved, 1) == reciprocal_rank(gold, retrieved, 1) == 0
    assert recall_at_k([page(1), page(1)], [page(1)], 5) == 1
    assert reciprocal_rank(gold, [], 5) == 0
    assert recall_at_k([page(1)], [page(1, "b" * 64)], 5) == 0


@pytest.mark.parametrize("metric", [recall_at_k, reciprocal_rank])
def test_page_metrics_require_gold_and_positive_k(metric):
    with pytest.raises(ValueError):
        metric([], [page(1)], 5)
    with pytest.raises(ValueError):
        metric([page(1)], [], 0)


def test_hand_computed_citation_and_refusal_rates_have_no_vacuous_perfection():
    assert citation_validity(2, 3) == pytest.approx(2 / 3)
    assert refusal_accuracy(2, 3) == pytest.approx(2 / 3)
    assert citation_validity(0, 0) is None
    assert refusal_accuracy(0, 0) is None
    for metric in (citation_validity, refusal_accuracy):
        for counts in ((-1, 2), (3, 2), (0, -1)):
            with pytest.raises(ValueError):
                metric(*counts)


def test_hand_computed_latency_percentiles():
    assert percentile([4, 1, 3, 2], 0.5) == 2.5
    assert percentile([4, 1, 3, 2], 0.95) == pytest.approx(3.85)
    assert percentile([7], 0.95) == 7
    assert percentile([1, 2], 0) == 1
    assert percentile([1, 2], 1) == 2
    assert percentile([], 0.5) is None


@pytest.mark.parametrize(
    "values,quantile",
    [([-1], 0.5), ([float("nan")], 0.5), ([float("inf")], 0.5), ([1], -0.1), ([1], 1.1)],
)
def test_latency_rejects_invalid_samples(values, quantile):
    with pytest.raises(ValueError):
        percentile(values, quantile)


def test_golden_digest_and_optional_reference_answers(tmp_path):
    path = tmp_path / "golden.jsonl"
    raw = (
        json.dumps(row(reference_answer="Human-authored test reference"))
        + "\n\n"
        + json.dumps(
            row(
                id="negative",
                question="Synthetic negative fixture",
                answerable=False,
                gold_pages=[],
            )
        )
    )
    path.write_text(raw)
    questions, digest = load_golden(path, 2000)
    assert len(questions) == 2 and questions[0].reference_answer == "Human-authored test reference"
    assert not questions[1].answerable
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert GoldenQuestion.model_json_schema()["additionalProperties"] is False
    schema_path = Path(__file__).resolve().parents[3] / "eval/golden.schema.json"
    assert json.loads(schema_path.read_text()) == GoldenQuestion.model_json_schema()


@pytest.mark.parametrize(
    "updates",
    [
        {"answerable": "true"},
        {"question": " "},
        {"id": ""},
        {"unexpected": 1},
        {"gold_pages": []},
        {"answerable": False},
        {"gold_pages": [{"doc_id": "not-a-hash", "page": 1}]},
        {"gold_pages": [{"doc_id": "a" * 64, "page": True}]},
        {"gold_pages": [{"doc_id": "a" * 64, "page": 0}]},
        {"gold_pages": row()["gold_pages"] * 2},
        {"answerable": False, "gold_pages": [], "reference_answer": "inconsistent reference"},
        {"question": "x" * 2001},
        {"question": chr(0xD800)},
    ],
)
def test_invalid_labels_fail_without_echoing_row_contents(tmp_path, updates):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(row(**updates)))
    with pytest.raises(GoldenDataError, match="^Invalid golden row at line 1.$"):
        load_golden(path, 2000)


@pytest.mark.parametrize(
    "content",
    [
        "",
        " \n",
        "not JSON",
        "[]",
        '{"id":"a","id":"b"}',
        json.dumps(row()) + "\n" + json.dumps(row()),
        json.dumps(row()) + "\n" + json.dumps(row(id="other")),
    ],
)
def test_empty_malformed_and_duplicate_golden_data(tmp_path, content):
    path = tmp_path / "bad.jsonl"
    path.write_text(content)
    with pytest.raises(GoldenDataError):
        load_golden(path, 2000)


def test_golden_missing_file_and_invalid_utf8(tmp_path):
    with pytest.raises(GoldenDataError, match="UTF-8"):
        load_golden(tmp_path / "missing", 2000)
    path = tmp_path / "bad.jsonl"
    path.write_bytes(b"\xff")
    with pytest.raises(GoldenDataError, match="UTF-8"):
        load_golden(path, 2000)
