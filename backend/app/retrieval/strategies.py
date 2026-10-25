"""Three small retrieval strategies and rank-only Reciprocal Rank Fusion."""

from collections.abc import Callable, Sequence

from app.errors import ProviderError
from app.ingestion.service import validate_vectors
from app.providers.interfaces import EmbeddingProvider
from app.retrieval.interfaces import Retriever, SearchRepository
from app.retrieval.models import SearchHit
from app.settings import EMBEDDING_DIMENSIONS


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[SearchHit]],
    k: int,
    constant: int,
) -> list[SearchHit]:
    """Sum 1/(constant + one-based rank), counting each chunk once per ranking."""
    if k < 1 or constant < 0:
        raise ValueError("require k >= 1 and constant >= 0")
    scores: dict[int, float] = {}
    passages: dict[int, SearchHit] = {}
    for ranking in rankings:
        seen: set[int] = set()
        for rank, hit in enumerate(ranking, start=1):
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            passages.setdefault(hit.chunk_id, hit)
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1 / (constant + rank)
    fused = [
        hit.model_copy(update={"score": scores[chunk_id]}) for chunk_id, hit in passages.items()
    ]
    return sorted(
        fused, key=lambda hit: (-hit.score, hit.doc_id, hit.page, hit.chunk_index, hit.chunk_id)
    )[:k]


class VectorRetriever:
    """Embed a query once and delegate exact nearest-neighbor ranking to PostgreSQL."""

    def __init__(
        self,
        repository: SearchRepository,
        profile: str,
        provider_factory: Callable[[], EmbeddingProvider],
    ) -> None:
        self._repository = repository
        self._profile = profile
        self._provider_factory = provider_factory

    def search(self, query: str, k: int) -> list[SearchHit]:
        """Validate query vectors before asking the database to compare them."""
        provider = self._provider_factory()
        if provider.dimensions != EMBEDDING_DIMENSIONS:
            raise ProviderError("invalid_embedding_dimensions")
        vectors = provider.embed([query])
        validate_vectors(vectors, 1, EMBEDDING_DIMENSIONS)
        return self._repository.vector_search(self._profile, vectors[0], k)


class KeywordRetriever:
    """Use full-text search with no embedding-provider dependency or API calls."""

    def __init__(self, repository: SearchRepository, profile: str) -> None:
        self._repository = repository
        self._profile = profile

    def search(self, query: str, k: int) -> list[SearchHit]:
        """Return PostgreSQL keyword matches in rank order."""
        return self._repository.keyword_search(self._profile, query, k)


class HybridRetriever:
    """Combine independently ranked vector and keyword candidates using RRF."""

    def __init__(
        self,
        vector: Retriever,
        keyword: Retriever,
        candidate_k: int,
        constant: int,
    ) -> None:
        self._vector = vector
        self._keyword = keyword
        self._candidate_k = candidate_k
        self._constant = constant

    def search(self, query: str, k: int) -> list[SearchHit]:
        """Retrieve at least k candidates per source and fuse without raw-score mixing."""
        depth = max(k, self._candidate_k)
        return reciprocal_rank_fusion(
            [
                self._vector.search(query, depth),
                self._keyword.search(query, depth),
            ],
            k,
            self._constant,
        )
