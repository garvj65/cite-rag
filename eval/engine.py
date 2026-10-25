"""Measure each retrieval exactly once and evaluate its evidence-gated answer."""

import random
import time
from collections.abc import Callable, Sequence

from app.answering.models import AskResponse
from app.answering.service import AnswerService
from app.errors import (
    ModelOutputError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
)
from app.retrieval.models import SearchResponse
from app.retrieval.service import SearchService
from sqlalchemy.exc import SQLAlchemyError

from eval.metrics import (
    citation_validity,
    percentile,
    recall_at_k,
    reciprocal_rank,
    refusal_accuracy,
)
from eval.models import (
    EvaluationOptions,
    EvaluationResult,
    EvaluationRow,
    EvaluationSummary,
    RetrievedPage,
)
from eval.schema import GoldenQuestion, GoldPage


def evaluate_questions(
    questions: Sequence[GoldenQuestion],
    search: SearchService,
    answers: AnswerService,
    options: EvaluationOptions,
    metadata: dict[str, object],
    clock: Callable[[], float] = time.perf_counter,
    pause: Callable[[float], None] = time.sleep,
) -> EvaluationResult:
    """Use a seeded order, retain failures, and never mistake an outage for a refusal."""
    if not questions:
        raise ValueError("evaluation requires questions")
    ordered = list(questions)
    random.Random(options.seed).shuffle(ordered)
    rows: list[EvaluationRow] = []
    for position, question in enumerate(ordered):
        if position and options.question_delay_seconds:
            pause(options.question_delay_seconds)
        started = clock()
        retrieved_at = started
        retrieval: SearchResponse | None = None
        answer: AskResponse | None = None
        error: str | None = None
        try:
            retrieval = search.search(question.question, options.strategy, options.k)
            retrieved_at = clock()
            answer = answers.answer_from_retrieval(question.question, retrieval)
        except ProviderConfigurationError:
            error = "provider_not_configured"
        except ProviderTimeoutError:
            error = "provider_timeout"
        except ModelOutputError:
            error = "invalid_model_output"
        except ProviderError:
            error = "provider_failure"
        except SQLAlchemyError:
            error = "database_unavailable"
        finished = clock()
        if retrieval is None:
            retrieved_at = finished
        hits = retrieval.results if retrieval else []
        pages = [GoldPage(doc_id=hit.doc_id, page=hit.page) for hit in hits]
        rows.append(
            EvaluationRow(
                id=question.id,
                question=question.question,
                answerable=question.answerable,
                gold_pages=question.gold_pages,
                retrieved=[RetrievedPage(**hit.model_dump()) for hit in hits],
                answer=answer,
                error=error,
                recall=recall_at_k(question.gold_pages, pages, options.k)
                if question.answerable
                else None,
                reciprocal_rank=reciprocal_rank(question.gold_pages, pages, options.k)
                if question.answerable
                else None,
                retrieval_latency_ms=(retrieved_at - started) * 1000,
                latency_ms=(finished - started) * 1000,
            )
        )
    return EvaluationResult(options=options, metadata=metadata, summary=summarize(rows), rows=rows)


def summarize(rows: Sequence[EvaluationRow]) -> EvaluationSummary:
    """Macro-average page metrics and micro-average raw citation verification counts."""
    recalls = [row.recall for row in rows if row.recall is not None]
    ranks = [row.reciprocal_rank for row in rows if row.reciprocal_rank is not None]
    proposed = sum(row.answer.verification.proposed for row in rows if row.answer is not None)
    valid = sum(row.answer.verification.valid for row in rows if row.answer is not None)
    negatives = sum(not row.answerable for row in rows)
    refused = sum(
        not row.answerable and row.answer is not None and not row.answer.supported for row in rows
    )
    return EvaluationSummary(
        questions=len(rows),
        answerable=len(recalls),
        unanswerable=negatives,
        errors=sum(row.error is not None for row in rows),
        recall_at_k=sum(recalls) / len(recalls) if recalls else None,
        mrr=sum(ranks) / len(ranks) if ranks else None,
        citation_validity=citation_validity(valid, proposed),
        citations_proposed=proposed,
        citations_valid=valid,
        refusal_accuracy=refusal_accuracy(refused, negatives),
        correct_refusals=refused,
        latency_p50_ms=percentile([row.latency_ms for row in rows], 0.5),
        latency_p95_ms=percentile([row.latency_ms for row in rows], 0.95),
    )
