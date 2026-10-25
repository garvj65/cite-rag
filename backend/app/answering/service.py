"""Evidence-gated generation that refuses unverified citations instead of dropping evidence."""

import json
from collections.abc import Callable

from pydantic import ValidationError

from app.answering.citations import verify_citation
from app.answering.models import AskResponse, CitationVerification, ModelAnswer, VerifiedCitation
from app.answering.prompt import build_context, system_prompt
from app.errors import ModelOutputError
from app.providers.interfaces import LLMProvider
from app.retrieval.service import SearchService
from app.settings import RetrievalStrategy, Settings

REFUSAL_MESSAGE = "I couldn't find enough support for an answer in the documents."


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def parse_model_answer(raw: str, settings: Settings) -> ModelAnswer:
    """Reject invalid JSON, duplicate fields, coercions, extra fields, and oversized output."""
    if len(raw) > settings.model_max_output_characters:
        raise ModelOutputError("invalid_model_output")
    try:
        payload: object = json.loads(raw, object_pairs_hook=_unique_object)
        answer = ModelAnswer.model_validate(payload)
        # Reject decoded lone surrogates before the HTTP response encodes answer text.
        answer.answer.encode("utf-8")
        if (
            len(answer.answer) > settings.answer_max_characters
            or len(answer.citations) > settings.answer_max_citations
            or any(len(c.quote) > settings.answer_max_quote_characters for c in answer.citations)
            or (answer.supported and not answer.answer.strip())
        ):
            raise ValueError("model output outside configured limits")
    except (ValueError, ValidationError, RecursionError):
        raise ModelOutputError("invalid_model_output") from None
    return answer


class AnswerService:
    """Retrieve, gate evidence, generate strict JSON, and verify every proposed citation."""

    def __init__(
        self,
        settings: Settings,
        search: SearchService,
        llm_factory: Callable[[], LLMProvider],
    ) -> None:
        self._settings = settings
        self._search = search
        self._llm_factory = llm_factory

    def ask(
        self,
        query: str,
        strategy: RetrievalStrategy | None = None,
        k: int | None = None,
    ) -> AskResponse:
        """Return no answer text unless model support and every citation pass validation."""
        response = AskResponse(
            answer=REFUSAL_MESSAGE,
            citations=[],
            supported=False,
            reason="no_retrieval",
            mode="no_model",
            verification=CitationVerification(),
        )
        retrieval = self._search.search(query, strategy, k)
        if not retrieval.results:
            return response
        thresholds = {
            "vector": self._settings.answer_min_vector_score,
            "keyword": self._settings.answer_min_keyword_score,
            "hybrid": self._settings.answer_min_hybrid_score,
        }
        eligible = [hit for hit in retrieval.results if hit.score >= thresholds[retrieval.strategy]]
        if not eligible:
            return response.model_copy(update={"reason": "weak_retrieval"})
        context = build_context(query.strip(), eligible, self._settings.answer_context_characters)
        if not context.passages:
            return response.model_copy(update={"reason": "context_limit"})
        model = parse_model_answer(
            self._llm_factory().generate(system_prompt(), context.user_prompt), self._settings
        )
        resolved = [verify_citation(citation, context.passages) for citation in model.citations]
        counts = CitationVerification(
            proposed=len(resolved), valid=sum(c is not None for c in resolved)
        )
        response.mode = "scripted" if self._settings.llm_provider == "fake" else "model"
        response.verification = counts
        if not model.supported:
            response.reason = "model_unsupported"
            return response
        if not resolved or counts.valid != counts.proposed:
            response.reason = "invalid_citations"
            return response
        citations: list[VerifiedCitation] = []
        seen: set[tuple[str, int, str]] = set()
        for citation in resolved:
            if citation is not None:
                identity = (citation.doc_id, citation.page, citation.quote)
                if identity not in seen:
                    citations.append(citation)
                    seen.add(identity)
        return AskResponse(
            answer=model.answer.strip(),
            citations=citations,
            supported=True,
            reason="supported",
            mode=response.mode,
            verification=counts,
        )
