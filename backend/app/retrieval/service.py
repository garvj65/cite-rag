"""Validate search bounds and dispatch to one explicitly selected retriever."""

from collections.abc import Callable

from app.errors import SearchInputError
from app.ingestion.service import indexing_profile
from app.providers.interfaces import EmbeddingProvider
from app.retrieval.interfaces import Retriever, SearchRepository
from app.retrieval.models import ScoreType, SearchResponse
from app.retrieval.strategies import HybridRetriever, KeywordRetriever, VectorRetriever
from app.settings import RetrievalStrategy, Settings


class SearchService:
    """Search only the index matching the configured model and chunk settings."""

    def __init__(
        self,
        settings: Settings,
        repository: SearchRepository,
        provider_factory: Callable[[], EmbeddingProvider],
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._provider_factory = provider_factory
        self.profile = indexing_profile(settings)

    def search(
        self,
        query: str,
        strategy: RetrievalStrategy | None = None,
        k: int | None = None,
    ) -> SearchResponse:
        """Return top passages or an empty result; never silently change strategies."""
        if not query.strip() or len(query) > self._settings.max_query_characters:
            raise SearchInputError("Query must be nonempty and within the configured size limit.")
        count = self._settings.search_k if k is None else k
        if not 1 <= count <= self._settings.search_max_k:
            raise SearchInputError("Requested k is outside the configured result limit.")
        selected = self._settings.search_strategy if strategy is None else strategy
        score_types: dict[RetrievalStrategy, ScoreType] = {
            "vector": "cosine_similarity",
            "keyword": "fts_rank",
            "hybrid": "rrf",
        }
        vector = VectorRetriever(self._repository, self.profile, self._provider_factory)
        keyword = KeywordRetriever(self._repository, self.profile)
        retrievers: dict[RetrievalStrategy, Retriever] = {
            "vector": vector,
            "keyword": keyword,
            "hybrid": HybridRetriever(
                vector, keyword, self._settings.hybrid_candidate_k, self._settings.rrf_constant
            ),
        }
        results = (
            retrievers[selected].search(query.strip(), count)
            if self._repository.has_profile(self.profile)
            else []
        )
        return SearchResponse(
            strategy=selected,
            k=count,
            profile=self.profile,
            score_type=score_types[selected],
            results=results,
        )
