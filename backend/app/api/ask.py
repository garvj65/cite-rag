"""Cited-answer endpoint reusing search validation and request-scoped provider cleanup."""

from collections.abc import Iterator
from contextlib import ExitStack
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from app.answering.models import AskResponse
from app.answering.service import AnswerService
from app.api.search import SearchRequest, get_search_service
from app.providers.factory import create_llm_provider
from app.providers.interfaces import LLMProvider
from app.retrieval.service import SearchService
from app.settings import Settings

router = APIRouter()


def get_answer_service(
    request: Request,
    search: Annotated[SearchService, Depends(get_search_service)],
) -> Iterator[AnswerService]:
    """Keep generation lazy so weak/empty retrieval spends no chat-provider quota."""
    settings = cast(Settings, request.app.state.settings)
    with ExitStack() as stack:

        def llm_factory() -> LLMProvider:
            """Initialize a provider only after retrieval passes the evidence gates."""
            return create_llm_provider(settings, stack)

        yield AnswerService(settings, search, llm_factory)


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: SearchRequest,
    service: Annotated[AnswerService, Depends(get_answer_service)],
) -> AskResponse:
    """Answer from retrieved passages or return a fixed refusal without fabricated citations."""
    return service.ask(payload.query, payload.strategy, payload.k)
