"""Application/database wiring used only by explicit evaluation entry points."""

import hashlib
import platform
import subprocess
from collections.abc import Sequence
from contextlib import ExitStack
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

from app.answering.service import AnswerService
from app.db.models import Chunk, Document
from app.db.repository import create_db_engine
from app.ingestion.service import indexing_profile
from app.providers.factory import (
    configured_model_id,
    create_embedding_provider,
    create_llm_provider,
)
from app.providers.interfaces import EmbeddingProvider, LLMProvider
from app.retrieval.repository import PostgresSearchRepository
from app.retrieval.service import SearchService
from app.settings import Settings
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from eval.engine import evaluate_questions
from eval.models import EvaluationOptions, EvaluationResult
from eval.schema import GoldenDataError, GoldenQuestion, GoldPage

# An allowlist prevents future credentials/settings from leaking into saved experiment metadata.
PROVENANCE_SETTINGS = {
    "enable_real_providers",
    "embedding_provider",
    "gemini_embedding_model",
    "openai_embedding_model",
    "llm_provider",
    "gemini_chat_model",
    "openai_chat_model",
    "chunk_size_words",
    "chunk_overlap_words",
    "hybrid_candidate_k",
    "rrf_constant",
    "answer_min_vector_score",
    "answer_min_keyword_score",
    "answer_min_hybrid_score",
    "answer_context_characters",
    "answer_max_characters",
    "answer_max_citations",
    "answer_max_quote_characters",
    "model_max_output_characters",
    "chat_max_completion_tokens",
    "provider_timeout_seconds",
    "provider_max_attempts",
    "provider_backoff_seconds",
    "provider_max_backoff_seconds",
    "max_query_characters",
}


def inspect_index(
    engine: Engine, profile: str, questions: Sequence[GoldenQuestion]
) -> list[dict[str, object]]:
    """Require an existing matching profile and all gold pages before making provider calls."""
    with Session(engine) as session:
        indexed = set(
            GoldPage(doc_id=doc_id, page=page)
            for doc_id, page in session.execute(
                select(Chunk.doc_id, Chunk.page_number).where(Chunk.profile == profile).distinct()
            )
        )
        if not indexed:
            raise GoldenDataError(
                "No chunks match this index profile. Ingest this configuration first."
            )
        expected = {page for question in questions for page in question.gold_pages}
        if not expected.issubset(indexed):
            raise GoldenDataError("Some gold document/pages have no chunks in this index profile.")
        documents = session.scalars(
            select(Document)
            .where(Document.id.in_({page.doc_id for page in indexed}))
            .order_by(Document.id)
        ).all()
        return [
            {
                "doc_id": doc.id,
                "title": doc.title,
                "pdf_pages": doc.page_count,
                "indexed_pages": sorted(page.page for page in indexed if page.doc_id == doc.id),
            }
            for doc in documents
        ]


def git_revision() -> str:
    """Record the checked-out revision without network access or credential inspection."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def working_tree_dirty() -> bool | None:
    """Flag uncommitted changes without recording filenames or their contents."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def run_evaluation(
    settings: Settings,
    questions: Sequence[GoldenQuestion],
    golden_sha256: str,
    options: EvaluationOptions,
) -> EvaluationResult:
    """Run the configured providers on one validated index, always closing owned resources."""
    if options.k > settings.search_max_k:
        raise GoldenDataError("Evaluation k exceeds SEARCH_MAX_K.")
    if not questions:
        raise GoldenDataError("Golden data is empty.")
    engine = create_db_engine(settings)
    try:
        corpus = inspect_index(engine, indexing_profile(settings), questions)
        with ExitStack() as stack:

            @cache
            def embedding_provider() -> EmbeddingProvider:
                """Reuse one client across this sequential evaluation."""
                return create_embedding_provider(settings, stack)

            @cache
            def chat_provider() -> LLMProvider:
                """Reuse the real client; scripted providers are constructed per question."""
                return create_llm_provider(settings, stack)

            search = SearchService(
                settings,
                PostgresSearchRepository(engine),
                embedding_provider,
            )
            answers = AnswerService(
                settings,
                search,
                lambda: (
                    create_llm_provider(settings, stack)
                    if settings.llm_provider == "fake"
                    else chat_provider()
                ),
            )
            return evaluate_questions(
                questions,
                search,
                answers,
                options,
                {
                    "created_at": datetime.now(UTC).isoformat(),
                    "git_commit": git_revision(),
                    "working_tree_dirty": working_tree_dirty(),
                    "python_version": platform.python_version(),
                    "scripted_response_sha256": hashlib.sha256(
                        settings.fake_llm_response.encode()
                    ).hexdigest()
                    if settings.llm_provider == "fake"
                    else None,
                    "golden_sha256": golden_sha256,
                    "index_profile": search.profile,
                    "embedding_model": configured_model_id(settings),
                    "mechanics_only": settings.embedding_provider == "fake"
                    or (not options.retrieval_only and settings.llm_provider == "fake"),
                    "settings": settings.model_dump(mode="json", include=PROVENANCE_SETTINGS),
                    "corpus": corpus,
                    "faithfulness": "not measured; no LLM judge",
                },
            )
    finally:
        engine.dispose()
