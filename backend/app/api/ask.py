"""Cited-answer endpoint reusing search validation and request-scoped provider cleanup."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from app.answering.models import AskResponse
from app.answering.service import AnswerService
from app.api.search import SearchRequest, get_search_service
from app.deadlines import execute_with_deadline
from app.providers.factory import create_llm_provider
from app.providers.interfaces import LLMProvider
from app.retrieval.service import SearchService
from app.settings import Settings

router = APIRouter()


def get_answer_service(
    request: Request,
    search_scope: Annotated[
        Callable[[], AbstractContextManager[SearchService]], Depends(get_search_service)
    ],
) -> Callable[[], AbstractContextManager[AnswerService]]:
    """Keep generation lazy so weak/empty retrieval spends no chat-provider quota."""
    settings = cast(Settings, request.app.state.settings)

    @contextmanager
    def scope() -> Iterator[AnswerService]:
        with search_scope() as search, ExitStack() as stack:

            def llm_factory() -> LLMProvider:
                """Initialize a provider only after retrieval passes the evidence gates."""
                return create_llm_provider(settings, stack)

            yield AnswerService(settings, search, llm_factory)

    return scope


@router.post("/ask", response_model=AskResponse)
async def ask(
    payload: SearchRequest,
    request: Request,
    service_scope: Annotated[
        Callable[[], AbstractContextManager[AnswerService]], Depends(get_answer_service)
    ],
) -> AskResponse:
    """Answer from retrieved passages or return a fixed refusal without fabricated citations."""

    def operation() -> AskResponse:
        with service_scope() as service:
            return service.ask(payload.query, payload.strategy, payload.k)

    settings = cast(Settings, request.app.state.settings)
    return await execute_with_deadline(operation, settings.request_deadline_seconds)
