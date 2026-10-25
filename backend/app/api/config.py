"""Expose only public query controls, never provider credentials or connection settings."""

from typing import cast

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.settings import RetrievalStrategy, Settings

router = APIRouter()


class ClientConfig(BaseModel):
    """Describe the backend-owned limits and defaults needed by the research interface."""

    max_query_characters: int
    search_strategy: RetrievalStrategy
    search_k: int
    search_max_k: int


@router.get("/config", response_model=ClientConfig)
def client_config(request: Request) -> ClientConfig:
    """Return an explicit allowlist of public settings without any database/model call."""
    settings = cast(Settings, request.app.state.settings)
    return ClientConfig(
        max_query_characters=settings.max_query_characters,
        search_strategy=settings.search_strategy,
        search_k=settings.search_k,
        search_max_k=settings.search_max_k,
    )
