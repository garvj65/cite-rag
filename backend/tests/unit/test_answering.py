import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from app.answering.citations import normalize_whitespace, verify_citation
from app.answering.models import ModelCitation
from app.answering.prompt import build_context, system_prompt
from app.answering.service import REFUSAL_MESSAGE, AnswerService, parse_model_answer
from app.errors import ModelOutputError, ProviderError, ProviderTimeoutError
from app.providers.fakes import ScriptedLLMProvider
from app.retrieval.models import SearchHit, SearchResponse


def passage(text="Keep the original document and record its source.", **updates):
    return SearchHit(
        **{
            "chunk_id": 1,
            "doc_id": "a" * 64,
            "document_title": "Offline fixture",
            "source": "Test fixture",
            "source_url": "https://example.test/source.pdf",
            "page": 2,
            "chunk_index": 0,
            "text": text,
            "score": 0.9,
            **updates,
        }
    )


def model_json(**updates):
    return json.dumps(
        {
            "answer": "Keep the original document and record its source.",
            "citations": [{"doc_id": "a" * 64, "page": 2, "quote": "Keep the original document"}],
            "supported": True,
            **updates,
        }
    )


def make_service(settings, hits, raw, strategy="vector", **config):
    search = Mock()
    search.search.return_value = SearchResponse(
        strategy=strategy,
        k=5,
        profile="profile",
        score_type={"vector": "cosine_similarity", "keyword": "fts_rank", "hybrid": "rrf"}[
            strategy
        ],
        results=hits,
    )
    fake = ScriptedLLMProvider([raw])
    factory = Mock(return_value=fake)
    settings = settings.model_copy(update={"llm_provider": "fake", **config})
    return AnswerService(settings, search, factory), fake, factory


def test_supported_answer_uses_verified_metadata_and_normalized_quote(settings):
    raw = model_json(
        citations=[{"doc_id": "a" * 64, "page": 2, "quote": " Keep\n the\t original   document "}]
    )
    service, fake, factory = make_service(settings, [passage()], raw)
    answer = service.ask("What should be retained?")
    assert answer.supported and answer.reason == "supported" and answer.mode == "scripted"
    assert answer.citations[0].quote == "Keep the original document"
    assert answer.citations[0].source_url == "https://example.test/source.pdf"
    assert answer.citations[0].chunk_id == 1 and answer.citations[0].page == 2
    assert answer.verification.proposed == answer.verification.valid == 1
    factory.assert_called_once()
    assert json.loads(fake.calls[0][1])["passages"][0]["number"] == 1


@pytest.mark.parametrize(
    ("strategy", "score"), [("vector", 0.1), ("keyword", 0.001), ("hybrid", 0.01)]
)
def test_weak_retrieval_spends_no_chat_calls(settings, strategy, score):
    service, fake, factory = make_service(settings, [passage(score=score)], model_json(), strategy)
    answer = service.ask("question")
    assert not answer.supported and answer.reason == "weak_retrieval"
    assert answer.answer == REFUSAL_MESSAGE and answer.citations == [] and answer.mode == "no_model"
    assert not fake.calls
    factory.assert_not_called()


def test_empty_retrieval_spends_no_chat_calls(settings):
    service, fake, factory = make_service(settings, [], model_json())
    answer = service.ask("question")
    assert answer.reason == "no_retrieval" and not answer.supported and not answer.citations
    factory.assert_not_called()
    assert not fake.calls


def test_model_unsupported_ignores_untrusted_answer_and_retains_counts(settings):
    service, _, _ = make_service(
        settings, [passage()], model_json(supported=False, answer="An untrusted unsupported answer")
    )
    answer = service.ask("question")
    assert answer.answer == REFUSAL_MESSAGE and answer.reason == "model_unsupported"
    assert answer.citations == [] and answer.verification.proposed == 1
    assert answer.verification.valid == 1


@pytest.mark.parametrize(
    "citation",
    [
        {"doc_id": "other", "page": 2, "quote": "Keep the original document"},
        {"doc_id": "a" * 64, "page": 1, "quote": "Keep the original document"},
        {"doc_id": "a" * 64, "page": 2, "quote": "fabricated passage"},
        {"doc_id": "a" * 64, "page": 2, "quote": "keep the original document"},
        {"doc_id": "a" * 64, "page": 2, "quote": "Keep the original … source."},
        {"doc_id": "a" * 64, "page": 2, "quote": " \t\n "},
    ],
)
def test_wrong_citations_refuse_without_releasing_answer(settings, citation):
    service, _, _ = make_service(settings, [passage()], model_json(citations=[citation]))
    answer = service.ask("question")
    assert answer.reason == "invalid_citations" and not answer.supported
    assert answer.answer == REFUSAL_MESSAGE and answer.citations == []
    assert answer.verification.proposed == 1 and answer.verification.valid == 0


def test_one_invalid_citation_suppresses_whole_answer(settings):
    citations = json.loads(model_json())["citations"]
    citations.append({"doc_id": "a" * 64, "page": 2, "quote": "invented text"})
    service, _, _ = make_service(settings, [passage()], model_json(citations=citations))
    answer = service.ask("question")
    assert not answer.supported and answer.citations == []
    assert (answer.verification.proposed, answer.verification.valid) == (2, 1)


def test_missing_citations_refuse_and_duplicates_are_deduplicated(settings):
    service, _, _ = make_service(settings, [passage()], model_json(citations=[]))
    assert service.ask("question").reason == "invalid_citations"
    citations = json.loads(model_json())["citations"] * 2
    service, _, _ = make_service(settings, [passage()], model_json(citations=citations))
    answer = service.ask("question")
    assert answer.supported and len(answer.citations) == 1
    assert answer.verification.proposed == answer.verification.valid == 2


def test_quote_cannot_span_two_chunks_or_use_unretrieved_chunk(settings):
    quote = ModelCitation(doc_id="a" * 64, page=2, quote="first second")
    assert verify_citation(quote, [passage("first"), passage("second", chunk_id=2)]) is None
    assert verify_citation(quote, []) is None
    assert normalize_whitespace("a\n\tb\u00a0c") == "a b c"


def test_context_budget_includes_only_complete_passages_and_counts_json_escaping(settings):
    hits = [passage('"' * 2000), passage("Short evidence.", chunk_id=2)]
    context = build_context("question", hits, 400)
    assert len(context.user_prompt) <= 400
    assert [hit.chunk_id for hit in context.passages] == [2]
    assert json.loads(context.user_prompt)["passages"][0]["number"] == 1
    service, _, factory = make_service(
        settings, [hits[0]], model_json(), answer_context_characters=400
    )
    assert service.ask("question").reason == "context_limit"
    factory.assert_not_called()


def test_quotes_in_context_excluded_chunks_are_invalid(settings):
    hits = [passage("x" * 2000), passage("Short evidence.", chunk_id=2)]
    raw = model_json(citations=[{"doc_id": "a" * 64, "page": 2, "quote": "xxxx"}])
    service, _, _ = make_service(settings, hits, raw, answer_context_characters=400)
    assert service.ask("question").reason == "invalid_citations"


def test_weak_passages_are_not_shown_to_model(settings):
    service, fake, _ = make_service(
        settings, [passage(), passage("weak text", score=0.1)], model_json()
    )
    assert service.ask("question").supported
    assert len(json.loads(fake.calls[0][1])["passages"]) == 1


def test_injected_passage_stays_in_json_data_and_fabricated_citations_fail(settings):
    injection = (Path(__file__).parents[1] / "fixtures/injected-passage.txt").read_text()
    raw = model_json(
        answer="PWNED",
        citations=[{"doc_id": "invented", "page": 99, "quote": "not in the document"}],
    )
    service, fake, _ = make_service(settings, [passage(injection)], raw)
    answer = service.ask("A legitimate user question")
    assert not answer.supported and answer.answer == REFUSAL_MESSAGE
    system, user = fake.calls[0]
    assert "Never obey" in system and "untrusted data" in system
    assert injection not in system
    data = json.loads(user)
    assert data["question"] == "A legitimate user question"
    assert data["passages"][0]["text"] == injection
    assert len(data["passages"]) == 1
    assert system_prompt() == system


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "```json\n{}\n```",
        "[]",
        "{}",
        model_json(supported="true"),
        model_json(answer=" "),
        model_json(extra="field"),
        model_json(citations=[{"doc_id": "a", "page": True, "quote": "text"}]),
        model_json(
            citations=[{"doc_id": "a", "page": 1, "quote": "text", "source_url": "invented"}]
        ),
        '{"answer":"x","citations":[],"supported":false,"supported":true}',
    ],
)
def test_malformed_model_output_is_an_error_not_a_document_refusal(settings, raw):
    service, _, _ = make_service(settings, [passage()], raw)
    with pytest.raises(ModelOutputError, match="^invalid_model_output$"):
        service.ask("question")


@pytest.mark.parametrize(
    ("update", "raw"),
    [
        ({"model_max_output_characters": 5}, model_json()),
        ({"answer_max_characters": 5}, model_json()),
        (
            {"answer_max_citations": 1},
            model_json(citations=json.loads(model_json())["citations"] * 2),
        ),
        ({"answer_max_quote_characters": 3}, model_json()),
    ],
)
def test_model_output_bounds(settings, update, raw):
    with pytest.raises(ModelOutputError):
        parse_model_answer(raw, settings.model_copy(update=update))


@pytest.mark.parametrize("failure", [ProviderError("private"), ProviderTimeoutError("private")])
def test_chat_failures_propagate_for_api_error_handling(settings, failure):
    service, _, _ = make_service(settings, [passage()], failure)
    with pytest.raises(type(failure)):
        service.ask("question")


def test_real_mode_is_explicit_in_response(settings):
    service, _, _ = make_service(settings, [passage()], model_json(), llm_provider="gemini")
    assert service.ask("question").mode == "model"
