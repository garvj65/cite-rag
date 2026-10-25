"""HTTP boundary for profile-scoped retrieval and lazy provider construction."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Engine

from app.deadlines import execute_with_deadline
from app.providers.factory import create_embedding_provider
from app.providers.interfaces import EmbeddingProvider
from app.retrieval.models import SearchResponse
from app.retrieval.repository import PostgresSearchRepository
from app.retrieval.service import SearchService
from app.settings import RetrievalStrategy, Settings

router = APIRouter()


class SearchRequest(BaseModel):
    """Accept a nonempty question with optional strategy and result-count overrides."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    query: str = Field(min_length=1)
    strategy: RetrievalStrategy | None = None
    k: int | None = Field(default=None, ge=1)

    @field_validator("query")
    @classmethod
    def validate_unicode(cls, value: str) -> str:
        """Reject lone surrogates before database/provider UTF-8 serialization."""
        value.encode("utf-8")
        return value


def get_search_service(request: Request) -> Callable[[], AbstractContextManager[SearchService]]:
    """Return a scope entered in the worker so cancellation cannot close active clients."""
    settings = cast(Settings, request.app.state.settings)
    engine = cast(Engine, request.app.state.db_engine)

    @contextmanager
    def scope() -> Iterator[SearchService]:
        with ExitStack() as stack:

            def provider_factory() -> EmbeddingProvider:
                """Open a provider client only when vector retrieval actually needs it."""
                return create_embedding_provider(settings, stack)

            yield SearchService(settings, PostgresSearchRepository(engine), provider_factory)

    return scope


@router.post("/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    request: Request,
    service_scope: Annotated[
        Callable[[], AbstractContextManager[SearchService]], Depends(get_search_service)
    ],
) -> SearchResponse:
    """Return ranked chunks and citation metadata without generating an answer."""

    def operation() -> SearchResponse:
        with service_scope() as service:
            return service.search(payload.query, payload.strategy, payload.k)

    settings = cast(Settings, request.app.state.settings)
    return await execute_with_deadline(operation, settings.request_deadline_seconds)
