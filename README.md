# CiteRAG

A staged RAG application for answers with verifiable document, page, and quote
citations. **M1 PDF ingestion and M2 retrieval are implemented.** `/search`
returns passages using vector, keyword, or hybrid retrieval. Answer generation,
citation verification, the React UI, and evaluation arrive in M3–M4.

[Learning guide](docs/learning-guide.md) · [Architecture](docs/architecture.md) ·
[M1 validation](docs/validation-m1.md) · [M2 validation](docs/validation-m2.md)

## Start locally

Prerequisites: Git and Docker Compose v2. From a fresh checkout:

```bash
git clone https://github.com/garvj65/cite-rag.git
cd cite-rag
cp .env.example .env
docker compose up --build --wait backend
```

While a milestone PR is under review, use its implementation branch. After
integration, `main` contains that milestone. Compose starts PostgreSQL 16 with
pgvector, applies Alembic migrations, and starts the API at
<http://localhost:8000>. Open `/docs` for the interactive search API.

The four commands start the API/database. Downloading and indexing the corpus
are explicit steps below. `/health` reports process liveness; Compose also
requires a healthy database and completed migrations. Real providers are disabled
by default. An empty matching index returns an empty results list.

## Download the starter corpus

Two related public NIST PDFs keep the corpus small. Their overlapping terminology
and different levels of detail provide material for retrieval comparisons. These
are fixed starter publications, not a claim to contain all current AI guidance.

| Document | PDF pages | Source |
|---|---:|---|
| AI Risk Management Framework 1.0 | 48 | [NIST AI 100-1, January 2023](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf) |
| Generative AI Risk Management Profile | 64 | [NIST AI 600-1, July 2024](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) |

After starting Compose, download using the existing image:

```bash
docker compose run --rm --user root --volume ./corpus:/app/corpus backend python scripts/download_corpus.py
```

The one-off downloader gets a writable bind mount. The API keeps its normal
non-root user and read-only corpus mount. Files downloaded this way can be owned
by root on Linux, but remain readable for ingestion. PDFs are gitignored.

Alternatively, with Python 3.12 and `uv` installed:

```bash
uv sync --frozen
uv run python scripts/download_corpus.py
```

The downloader validates YAML, bounds file size, checks the PDF signature, and
replaces files atomically. Cached files with a PDF header are reused. This does
not establish whether the remote resource changed or a cached PDF is complete;
delete a file explicitly to fetch it again. Ingestion parses the complete PDF
and identifies its original bytes by SHA-256.

## Configure and ingest

The default model configuration is **Gemini Embedding 2** for retrieval and
**Gemini 3.8 Flash** for M3 answers. The user's free-model preference updates the
original OpenAI-only specification. The original `text-embedding-3-small` option
remains selectable behind the same interface. No automatic provider fallback
exists, and no local model/GPU is required.

Google lists free API tiers for both suggested models as of 2026-10-24, subject
to quotas, account/region eligibility, availability, and terms. Use a free-tier
project; the application cannot enforce your account's billing configuration.
See [pricing](https://ai.google.dev/gemini-api/docs/pricing),
[rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), and
[OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai). Free-tier
content may be used to improve Google's products; the selected PDFs are public.

For real embeddings, edit the local `.env`:

```dotenv
EMBEDDING_PROVIDER=gemini
ENABLE_REAL_PROVIDERS=true
GEMINI_API_KEY=your-local-key
```

For an explicit keyless mechanics demo, instead select:

```dotenv
EMBEDDING_PROVIDER=fake
ENABLE_REAL_PROVIDERS=false
```

Fake embeddings are deterministic lexical hashes. They support repeatable
mechanics tests and a keyless demo; they do not establish semantic retrieval
quality. There is no implicit switch into fake mode. Real-provider contracts
have mocked coverage, but authenticated model calls have not been verified yet.

After editing `.env`, recreate the backend and ingest:

```bash
docker compose up --wait backend
docker compose exec backend python -m app.ingest --path corpus/
```

`--fake` remains available as a CLI-only override. To search its resulting index,
set the API's `EMBEDDING_PROVIDER=fake` too. Ingestion and the API must use the
same provider/model, chunk size, and overlap: the resulting profile hash keeps
incompatible embedding spaces and chunk experiments separate. Unchanged bytes
with unchanged settings are skipped, including renamed files.

Progress goes to stderr. Stdout contains JSON counts for newly indexed documents,
pages, chunks, skipped files, failures, and reason codes. Exit codes: 0 for a
completed scan including skips, 1 for processing/database failures, and 2 for
invalid input/configuration. Empty, corrupt, encrypted, scanned/no-text,
oversized, and excessive-page PDFs have explicit skip reasons. Empty pages inside
an otherwise extractable document retain their physical PDF page numbering.

## Search

Use `/docs` in a browser or send:

```bash
curl http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"risk management","strategy":"hybrid","k":5}'
```

`query` is required. `strategy` and `k` default to environment settings.

| Strategy | Behavior | Response score type |
|---|---|---|
| `vector` | Exact cosine search in pgvector; one question embedding call | `cosine_similarity` |
| `keyword` | PostgreSQL English FTS via `websearch_to_tsquery` and `ts_rank_cd`; no embedding call | `fts_rank` |
| `hybrid` | Fuse vector and keyword candidate rankings using RRF | `rrf` |

The response includes `strategy`, requested `k`, `profile`, `score_type`, and
`results`. Each result contains `chunk_id`, `doc_id`, `document_title`, `source`,
`source_url`, one-based physical PDF `page`, zero-based per-page `chunk_index`,
exact stored `text`, and `score`. A page label printed in a document may differ
from the physical PDF page number. No generated answer or model-selected quote
is returned in M2.

Scores order passages within their strategy. Their scales differ and are not
confidence probabilities. Vector retrieval can return weakly related passages;
answer support/refusal decisions belong to M3. All strategies isolate the same
index profile and use deterministic tie-breaking.

An empty index returns HTTP 200 with `results: []`, without creating a provider
client. Keyword requests also make no provider call, including when real-provider
credentials are disabled after a corpus has already been indexed.

| HTTP status | Meaning |
|---|---|
| 422 | Invalid fields, empty/oversized query, unsupported strategy, or k outside configured limits |
| 502 | Embedding provider failed or returned an invalid vector response |
| 503 | Database unavailable or required embedding provider unconfigured |
| 504 | Embedding provider exhausted its timeout retries |

Errors use `{"error":{"code":"...","message":"..."}}` without raw provider
bodies, rejected payloads, credentials, SQL, or stack traces. Vector/hybrid
requests do not silently fall back to keyword search on provider failure.

## Configuration and design

Settings are typed in `backend/app/settings.py`; `.env.example` documents them.

| Setting | Default | Meaning |
|---|---:|---|
| `CHUNK_SIZE_WORDS` | 400 | Maximum words per within-page chunk |
| `CHUNK_OVERLAP_WORDS` | 80 | Shared words between consecutive windows |
| `EMBEDDING_BATCH_SIZE` | 16 | Number of passages sent per embedding batch |
| `SEARCH_STRATEGY` | hybrid | Default search strategy |
| `SEARCH_K` | 5 | Default result count |
| `SEARCH_MAX_K` | 50 | Maximum request result count |
| `MAX_QUERY_CHARACTERS` | 2000 | Maximum normalized query length |
| `HYBRID_CANDIDATE_K` | 20 | Candidate depth per source, increased to k when necessary |
| `RRF_CONSTANT` | 60 | Denominator offset for one-based fusion ranks |

Provider timeouts, bounded exponential-backoff retries, and PDF size/page limits
are configurable too. Permanent provider errors and invalid responses fail
without retrying. Persistent quota exhaustion requires waiting before retrying
the CLI. No API keys or full document text are logged at INFO.

```mermaid
flowchart TD
    P["PDFs and manifest"] --> I["Extract pages and chunk"]
    I --> E["Embed passages"]
    E --> D["PostgreSQL: text, metadata, vectors, FTS"]
    Q["Question"] --> S["Selected retrieval strategy"]
    D --> S
    S --> R["Ranked passages and source metadata"]
```

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16, and
  pgvector. `uv.lock` pins dependencies.
- Page-limited word windows preserve exact offsets into canonical normalized
  text. Word counts are not model-token budgets.
- SHA-256 identities and database constraints handle duplicates. A document's
  pages and chunks commit atomically after embedding succeeds.
- FTS migration 0002 populates existing M1 chunks automatically. Vector search
  remains exact for a clear correctness baseline.
- Hybrid RRF sums `1 / (constant + rank)` rather than adding incompatible raw
  scores. Each chunk contributes at most once per source ranking.
- No orchestration framework, queue, OCR, or extra storage service is introduced.

## Verification

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Tests block external Python sockets and mock provider HTTP. Integration tests
require `TEST_DATABASE_URL` pointing to a local PostgreSQL 16/pgvector database
whose name ends in `_test`. They truncate application tables and test migration
changes; never point them at useful data. Without that variable the database
tests are explicitly skipped. CI always supplies the database service.

CI enforces at least 85% backend application coverage and runs lint, formatting,
strict application/script typing, tests against PostgreSQL, the Docker build,
and Compose configuration validation. It also starts the actual stack, checks
health, ingests an offline generated one-page PDF twice to test idempotency,
and sends vector, keyword, and hybrid searches to the running HTTP API. These
checks use explicit fake embeddings and make no authenticated model calls.

M2 verification: **143 tests passed, including all 15 PostgreSQL integration tests,
with 99.74% backend application coverage**. Lint, formatting, strict mypy, the
Docker build, and the complete Compose ingestion/search smoke check passed.
See [the M2 validation record](docs/validation-m2.md) for the exact run and scope.
The React/Vite UI and frontend checks are scheduled for M3.

## Evaluation status

| Strategy | Recall@5 | MRR | Citation validity | Refusal accuracy | Latency p50/p95 |
|---|---|---|---|---|---|
| Vector | Pending M4 | Pending | Pending | Pending | Pending |
| Keyword | Pending M4 | Pending | Pending | Pending | Pending |
| Hybrid | Pending M4 | Pending | Pending | Pending | Pending |

No questions, gold answers, or retrieval-quality numbers have been invented.
The user writes the golden data in M4; model-quality evaluation needs an explicit
real-provider run. Mechanical ranking tests and code coverage are not semantic
retrieval or answer-quality measurements.

## Limitations and next milestone

- M2 returns passages. Cited answers, refusals, the frontend, and the evaluation
  harness are M3–M4 work.
- Extraction cannot OCR scans or reliably reconstruct tables, multi-column
  layouts, equations, or images. Page boundaries can divide useful context.
- English full-text search is appropriate for this corpus; other languages need
  a deliberate search configuration change.
- Very long chunks can exceed a provider's token limit. They fail without silently
  truncating evidence. Exact vector search trades scalability for a simple baseline.
- Identical PDF bytes retain first-ingestion source metadata. Changes to extraction
  semantics need a deliberate migration/reindex procedure.
- Concurrent ingestions can consume duplicate embedding quota while database rows
  remain deduplicated. In-flight embeddings are not cached.
- The Compose password is a labeled local-development example. Deployment
  instructions, a public-demo operating model, and a UI screenshot arrive with
  later milestones. No production deployment is claimed.
