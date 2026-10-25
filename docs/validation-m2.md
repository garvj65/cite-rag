# M2 validation record

Verified on 2026-10-25 against implementation commit
`c7d5db0a750f82b52be5ec7ae4453ad820e83215`.

[CI run](https://github.com/garvj65/cite-rag/actions/runs/40163245109) passed:

| Check | Measured result |
|---|---|
| Ruff lint and formatting | Passed |
| Strict mypy on application and scripts | Passed, 28 source files |
| Pytest with PostgreSQL 16/pgvector | 143 passed, 0 skipped |
| PostgreSQL integration tests within that total | 15 passed |
| Backend application coverage, including branches | 99.74% |
| Backend Docker build | Passed |
| Compose configuration and complete startup | Passed |
| Compose ingestion and duplicate skipping | Passed |
| Vector, keyword, and hybrid search through the running HTTP API | Passed |

## Behavior checked

- Exact cosine ordering using deterministic hash embeddings, native PostgreSQL
  keyword ranking, stemming, phrase parsing, stop-word/empty results, and query
  parameterization.
- Correct document/page/source metadata, result limits, deterministic tie-breaking,
  and isolation between different chunk/model indexing profiles.
- RRF hand calculations with one-based ranks, missing contributors, duplicate
  contributors, ties, and raw scores on different scales.
- Empty, blank, oversized, and malformed requests; invalid strategy/k values;
  missing provider configuration, provider failures/timeouts, malformed vectors,
  and database failures. Error responses hide raw payloads, secrets, and SQL.
- Keyword and empty-index requests create no embedding provider. Vector/hybrid
  failures remain explicit errors without a hidden strategy/model fallback.
- Upgrading an M1 database populates FTS vectors for existing chunks. Migration
  downgrade/upgrade, concurrent duplicate ingestion, and atomic rollback remain tested.
- The actual Compose deployment was started, not just built. Its offline fixture
  was ingested twice; all three `/search` strategies returned the expected stored
  passage and its document/page metadata through HTTP.

Tests block external Python sockets and mock provider HTTP. CI's PostgreSQL test
service and Compose application database are separate disposable databases.
Local checks passed 128 tests with 15 database tests explicitly skipped and
95.03% coverage; CI completed all database checks afterward.

## Measurement boundaries

The tiny ranking corpus and smoke PDF are offline test fixtures, not NIST golden
questions or gold answers. The tests establish deterministic ranking mechanics,
storage behavior, and API contracts. They do not measure Gemini semantic quality.

No authenticated Gemini/OpenAI call was made, no paid provider fallback exists,
and no real-provider compatibility or semantic-retrieval benchmark is claimed.
Real model validation still requires a configured API key. Recall, MRR, citation
validity, refusal accuracy, and latency benchmarks remain M4 work with user-authored
golden data. Answer generation and the React UI remain M3 work.
