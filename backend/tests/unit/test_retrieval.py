from contextlib import ExitStack
from unittest.mock import Mock

import pytest
from app.errors import (
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    SearchInputError,
)
from app.ingestion.service import indexing_profile
from app.providers.factory import configured_model_id, create_embedding_provider
from app.providers.fakes import HashEmbeddingProvider
from app.providers.http import HTTPEmbeddingProvider
from app.retrieval.models import SearchHit
from app.retrieval.service import SearchService
from app.retrieval.strategies import reciprocal_rank_fusion
from pydantic import SecretStr, ValidationError


def hit(chunk_id, score=1.0, doc_id=None):
    return SearchHit(
        chunk_id=chunk_id,
        doc_id=doc_id or str(chunk_id),
        document_title=f"Document {chunk_id}",
        source="Fixture",
        source_url=None,
        page=1,
        chunk_index=0,
        text=f"passage {chunk_id}",
        score=score,
    )


class StubSearchRepository:
    def __init__(self, present=True):
        self.present = present
        self.calls = []

    def has_profile(self, profile):
        self.calls.append(("exists", profile))
        return self.present

    def vector_search(self, profile, vector, k):
        self.calls.append(("vector", profile, k, vector))
        return [hit(1, 0.9), hit(2, 0.8)][:k]

    def keyword_search(self, profile, query, k):
        self.calls.append(("keyword", profile, k, query))
        return [hit(2, 0.2), hit(3, 0.1)][:k]


def test_rrf_hand_computed_ranks_ignore_incomparable_raw_scores():
    first, second, third = hit(1, 999.0), hit(2, -123.0), hit(3, 1.0)
    results = reciprocal_rank_fusion([[first, second], [second, third]], 3, 60)
    assert [item.chunk_id for item in results] == [2, 1, 3]
    assert [item.score for item in results] == pytest.approx(
        [
            1 / 62 + 1 / 61,
            1 / 61,
            1 / 62,
        ]
    )
    assert first.score == 999.0  # Fusion does not modify source results.


def test_rrf_ties_limits_empty_lists_and_duplicate_contributors():
    a, b = hit(1, doc_id="a"), hit(2, doc_id="b")
    assert reciprocal_rank_fusion([], 5, 60) == []
    assert [x.chunk_id for x in reciprocal_rank_fusion([[b], [a]], 1, 60)] == [1]
    assert reciprocal_rank_fusion([[], [a]], 2, 0)[0].score == 1.0
    assert reciprocal_rank_fusion([[a, a], [a]], 5, 60)[0].score == pytest.approx(2 / 61)
    tied = reciprocal_rank_fusion([[a, b], [b, a]], 5, 60)
    assert [x.chunk_id for x in tied] == [1, 2]
    assert tied[0].score == tied[1].score


@pytest.mark.parametrize(("k", "constant"), [(0, 60), (1, -1)])
def test_rrf_rejects_invalid_parameters(k, constant):
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], k, constant)


@pytest.mark.parametrize(
    ("strategy", "expected", "score_type"),
    [
        ("vector", [1, 2], "cosine_similarity"),
        ("keyword", [2, 3], "fts_rank"),
        ("hybrid", [2, 1], "rrf"),
    ],
)
def test_strategy_dispatch_profiles_and_lazy_embedding(settings, strategy, expected, score_type):
    config = settings.model_copy(update={"embedding_provider": "fake"})
    repository = StubSearchRepository()
    fake = HashEmbeddingProvider()
    factory = Mock(return_value=fake)
    response = SearchService(config, repository, factory).search("  apple  ", strategy, 2)
    assert [item.chunk_id for item in response.results] == expected
    assert response.score_type == score_type and response.k == 2
    assert response.profile == indexing_profile(config, fake)
    assert all(call[1] == response.profile for call in repository.calls)
    assert factory.call_count == (0 if strategy == "keyword" else 1)
    if strategy == "hybrid":
        assert response.results[0].vector_score == 0.8
        assert response.results[0].keyword_score == 0.2
        assert response.results[1].vector_score == 0.9
        assert response.results[1].keyword_score is None
        assert repository.calls[1][2] == config.hybrid_candidate_k
        assert repository.calls[2] == (
            "keyword",
            response.profile,
            config.hybrid_candidate_k,
            "apple",
        )
    elif strategy == "vector":
        assert response.results[0].vector_score == 0.9
    else:
        assert response.results[0].keyword_score == 0.2


def test_request_k_can_exceed_default_candidate_depth(settings):
    config = settings.model_copy(update={"hybrid_candidate_k": 1})
    repository = StubSearchRepository()
    SearchService(config, repository, HashEmbeddingProvider).search("apple", "hybrid", 3)
    assert [call[2] for call in repository.calls if call[0] != "exists"] == [3, 3]


def test_settings_defaults_are_used(settings):
    config = settings.model_copy(update={"search_strategy": "keyword", "search_k": 1})
    response = SearchService(config, StubSearchRepository(), Mock()).search("apple")
    assert response.strategy == "keyword" and response.k == 1 and len(response.results) == 1


@pytest.mark.parametrize("strategy", ["vector", "keyword", "hybrid"])
def test_empty_profile_avoids_all_model_calls(settings, strategy):
    repository, factory = StubSearchRepository(present=False), Mock(side_effect=AssertionError)
    response = SearchService(settings, repository, factory).search("apple", strategy)
    assert response.results == [] and len(repository.calls) == 1
    factory.assert_not_called()


@pytest.mark.parametrize(
    ("query", "k"), [("", 1), (" \t ", 1), ("x" * 2001, 1), ("apple", 0), ("apple", 51)]
)
def test_invalid_search_fails_before_any_database_or_model_call(settings, query, k):
    repository, factory = StubSearchRepository(), Mock()
    with pytest.raises(SearchInputError):
        SearchService(settings, repository, factory).search(query, k=k)
    assert not repository.calls
    factory.assert_not_called()


@pytest.mark.parametrize("exception", [ProviderError("private"), ProviderTimeoutError("private")])
def test_vector_and_hybrid_do_not_silently_fallback(settings, exception):
    for strategy in ("vector", "hybrid"):
        repository = StubSearchRepository()
        factory = Mock(side_effect=exception)
        with pytest.raises(type(exception)):
            SearchService(settings, repository, factory).search("apple", strategy)
        assert all(call[0] != "keyword" for call in repository.calls)


@pytest.mark.parametrize("vectors", [[], [[1.0]], [[0.0] * 1536], [[float("nan")] * 1536]])
def test_bad_query_embeddings_never_reach_database_search(settings, vectors):
    fake = Mock(dimensions=1536)
    fake.embed.return_value = vectors
    repository = StubSearchRepository()
    with pytest.raises(ProviderError):
        SearchService(settings, repository, lambda: fake).search("apple", "vector")
    assert len(repository.calls) == 1


def test_wrong_provider_dimension_is_rejected(settings):
    with pytest.raises(ProviderError, match="dimensions"):
        SearchService(settings, StubSearchRepository(), lambda: HashEmbeddingProvider(8)).search(
            "apple", "vector"
        )


@pytest.mark.parametrize("vendor", ["fake", "gemini", "openai"])
def test_configured_identity_matches_actual_provider(settings, vendor):
    config = settings.model_copy(
        update={
            "embedding_provider": vendor,
            "enable_real_providers": True,
            "gemini_api_key": SecretStr("test-key"),
            "openai_api_key": SecretStr("test-key"),
        }
    )
    with ExitStack() as stack:
        provider = create_embedding_provider(config, stack)
        assert configured_model_id(config) == provider.model_id
        assert indexing_profile(config) == indexing_profile(config, provider)


def test_fake_factory_is_explicit_and_does_not_create_http_client(settings, monkeypatch):
    def forbidden():
        raise AssertionError("fake provider must not initialize HTTP")

    monkeypatch.setattr("app.providers.factory.httpx.Client", forbidden)
    config = settings.model_copy(update={"embedding_provider": "fake"})
    with ExitStack() as stack:
        assert isinstance(create_embedding_provider(config, stack), HashEmbeddingProvider)
        with pytest.raises(ProviderConfigurationError):
            create_embedding_provider(settings, stack)
    # The real-only adapter must not interpret 'fake' as an OpenAI fallback.
    with pytest.raises(ProviderConfigurationError, match="fake_provider_requires_factory"):
        HTTPEmbeddingProvider(config.model_copy(update={"enable_real_providers": True}), Mock())


def test_search_default_limit_must_fit_configured_maximum():
    from app.settings import Settings

    with pytest.raises(ValidationError, match="search_max_k"):
        Settings(_env_file=None, search_k=6, search_max_k=5)
