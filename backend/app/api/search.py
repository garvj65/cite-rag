"""HTTP boundary for profile-scoped retrieval and lazy provider construction."""

from collections.abc import Iterator
from contextlib import ExitStack
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine

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


def get_search_service(request: Request) -> Iterator[SearchService]:
    """Keep database engines shared and provider HTTP clients scoped to one request."""
    settings = cast(Settings, request.app.state.settings)
    engine = cast(Engine, request.app.state.db_engine)
    with ExitStack() as stack:

        def provider_factory() -> EmbeddingProvider:
            """Open a provider client only when vector retrieval actually needs it."""
            return create_embedding_provider(settings, stack)

        yield SearchService(settings, PostgresSearchRepository(engine), provider_factory)


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchResponse:
    """Return ranked chunks and citation metadata without generating an answer."""
    return service.search(payload.query, payload.strategy, payload.k)
