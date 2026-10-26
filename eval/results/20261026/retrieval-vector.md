# CiteRAG evaluation

**Configured-provider evaluation — RETRIEVAL ONLY; no LLM calls or answer metrics**

| Mode | Strategy | Chunk words | k | Questions | Errors | Recall@k | MRR@k | Citation validity | Refusal accuracy | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| retrieval | vector | 400 | 5 | 30 | 0 | 0.8800 | 0.6747 | N/A | N/A | 221.6401 | 294.2316 |

Retrieval-only run: latency covers retrieval and bookkeeping only. Citations, refusals, and answer quality were not evaluated. N/A does not mean a perfect score or a failure.


Answerable: 25; unanswerable: 5; correct refusals: 0.
Raw citation counts before refusal filtering/deduplication: 0 valid / 0 proposed. Zero denominators are N/A.

Recall and MRR are macro averages over answerable questions. k counts chunks; recall deduplicates pages, while MRR uses the first matching chunk rank. Retrieval failures score zero; generation failures retain retrieval measurements. Errors are never counted as correct refusals. End-to-end latency includes retrieval, generation, validation, and retries for every attempted question, including failures. Intentional pauses between questions are excluded from latency.

No LLM judge is used. Citation validity measures quote provenance, not answer entailment. Faithfulness is not measured. A fixed seed controls question order; live providers, network conditions, database caches, and latencies are not bit-for-bit reproducible. Fake/mixed provider results are mechanics checks, not semantic-quality evidence.

## Reproduction metadata

```json
{
  "options": {
    "strategy": "vector",
    "k": 5,
    "seed": 42,
    "question_delay_seconds": 2.0,
    "retrieval_only": true
  },
  "created_at": "2026-10-26T05:48:17.908302+00:00",
  "git_commit": "764d21074b42007bb20e1c559a3ec48bebf20c61",
  "working_tree_dirty": false,
  "python_version": "3.12.3",
  "scripted_response_sha256": null,
  "golden_sha256": "b1307136fd933bf5b2cf36a1208304e1dfc06dc69f8c939a4a73b95e78224c56",
  "index_profile": "4a3e52273c1fcc3f62adc29a0d5a10b20b4b5757447d1fb87e8bf333686da91d",
  "embedding_model": "gemini/gemini-embedding-2",
  "mechanics_only": false,
  "settings": {
    "enable_real_providers": true,
    "embedding_provider": "gemini",
    "gemini_embedding_model": "gemini-embedding-2",
    "openai_embedding_model": "text-embedding-3-small",
    "llm_provider": "gemini",
    "gemini_chat_model": "gemini-3.6-flash",
    "openai_chat_model": "",
    "answer_min_vector_score": 0.35,
    "answer_min_keyword_score": 0.05,
    "answer_min_hybrid_score": 0.02,
    "answer_context_characters": 24000,
    "answer_max_characters": 12000,
    "answer_max_citations": 8,
    "answer_max_quote_characters": 2000,
    "model_max_output_characters": 50000,
    "chat_max_completion_tokens": 4096,
    "chunk_size_words": 400,
    "chunk_overlap_words": 80,
    "provider_timeout_seconds": 30.0,
    "provider_max_attempts": 3,
    "provider_backoff_seconds": 30.0,
    "provider_max_backoff_seconds": 60.0,
    "max_query_characters": 2000,
    "hybrid_candidate_k": 20,
    "rrf_constant": 60
  },
  "corpus": [
    {
      "doc_id": "6e73620ab6b64e90ef2c04bf0e0d6246185a2f4b1b13cab0df494496cff89b6a",
      "title": "NIST Generative AI Risk Management Profile",
      "pdf_pages": 64,
      "indexed_pages": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        46,
        47,
        48,
        49,
        50,
        51,
        52,
        53,
        54,
        55,
        56,
        57,
        58,
        59,
        60,
        61,
        62,
        63,
        64
      ]
    },
    {
      "doc_id": "7576edb531d9848825814ee88e28b1795d3a84b435b4b797d3670eafdc4a89f1",
      "title": "NIST AI Risk Management Framework 1.0",
      "pdf_pages": 48,
      "indexed_pages": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        46,
        47,
        48
      ]
    }
  ],
  "faithfulness": "not measured; no LLM judge"
}
```
