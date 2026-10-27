# Evaluate CiteRAG

The harness is implemented. At the user's explicit request on 2026-10-26,
`golden.jsonl` now contains an **assistant-authored baseline: 25 answerable questions
and 5 unanswerable questions**. Read [the answer key and evidence review](golden-review.md).
Source/hash/page/chunk checks passed. [The Flash-Lite quality pass](results/20261026_flashlite.md)
retains a zero-error hybrid answer run and one vector timeout, alongside the
[earlier frozen baseline](results/20261026_gemini_baseline.md).
The user confirmed reviewing the answer key on 2026-10-27 and kept q30 as an
ambiguous expected-refusal edge case. The golden file remains unchanged. Test/CI questions remain
separate synthetic fixtures. Empty datasets still fail validation.

For a browser-only run, use [GitHub Actions](#run-from-github-actions) below.
The [corpus reference](../docs/corpus-reference.md) gives verified document hashes
and physical page counts without requiring local ingestion.

## Run from GitHub Actions

No local installation is needed. The repository's `GEMINI_API_KEY` secret already
works; replace it only through **Settings → Secrets and variables → Actions**.
Never put its value in code, issues, logs, or chat.

1. Open **Actions → Explicit Gemini evaluation → Run workflow** and select the
   intended branch. Enable **Allow Gemini API calls** explicitly; otherwise no
   evaluation job runs. Ordinary CI always uses fakes.
2. Choose the model and strategy. `all` evaluates vector, keyword, then hybrid
   against **one index**, not three ingestions. Select `full` for all 30 questions
   or `wording-check` for q01/q02/q05/q08/q13/q20/q25/q30 only. The latter is a
   targeted regression check, not a replacement for the published benchmark.
3. Keep **Measure retrieval only** off for answer measurements. Enabling it
   makes no chat calls and marks answer metrics N/A. Browser checks default off;
   enable them only when UI wiring needs verification. They reuse this job's
   index and submit two additional real questions (q01/q05), saving original
   responses/screenshots. They do not contribute to benchmark metrics.
4. Review the run summary and download the **measured-evaluation** artifact within
   14 days. Keep errors, denominators, model/prompt revisions, original responses,
   and checksums when publishing reviewed results. Failed runs can contain useful
   measurements; never relabel errors as refusals or rerun only failures to replace rows.

A tiny provider preflight runs first; failure stops expensive indexing. After
verified corpus download, the workflow restores an exact-key cached PostgreSQL
snapshot or embeds/indexes once on a miss. The key includes PDF bytes, manifest,
indexing/model settings and code, migrations, and dependency lock. Prompt/chat-only
changes reuse embeddings. There are no prefix/fallback cache matches; every restore
must pass index/gold-page validation before evaluation. A bad restore fails without
silently re-embedding. Cache eviction/branch scope can require a fresh ingestion;
this is an optimization, not durable storage. To force a rebuild after a cache
problem, delete its **public-index** cache entry in Actions; do not edit golden labels.

Only the approved public corpus text, metadata, and vectors are cached, never a
connection string, API key, or chat response. Repository caches are not private
secret storage. The snapshot is restored only into the disposable evaluation DB.
Chromium binaries are cached by frontend lockfile; a fresh runner still installs
OS libraries when the optional browser check is requested. One workflow handles
measurements and browser checks; avoid launching a separate benchmark just for a
screenshot. Only this run's output directory is uploaded, not old committed reports.

Attempts/retries use process-local 12 chat attempts/minute and 90 embedding
inputs/minute for Flash-Lite; explicitly selected 3.6/3.8 use four chat attempts/minute.
Every embedding input is charged conservatively. Each cache miss indexes 149
chunks with current settings, plus preflight/query calls. Optional between-question
pauses are excluded from latency; in-request pacing/retries are included. Separate
processes/account users, token/daily quotas, and capacity are not controlled.
The shared quota screenshot described 28-day peak usage, not today's remaining balance.
The workflow never changes account billing or silently switches models.

## Author the golden file

Review the baseline, then add one JSON object per line in `eval/golden.jsonl`.
The current set contains the planned 25 answerable and 5 unanswerable questions.
Keep the same reviewed dataset across strategy comparisons.

| Field | Required | Meaning |
|---|---|---|
| `id` | Yes | Unique, nonempty stable identifier |
| `question` | Yes | Your question, within the backend query-length setting |
| `answerable` | Yes | Boolean determined by reading the corpus |
| `gold_pages` | Yes | Expected pages as objects with `doc_id` and `page`; empty for negatives |
| `reference_answer` | No | Reference answer for answerable rows; record authorship in the review notes; not automatically scored |

`doc_id` is the lowercase SHA-256 of original PDF bytes, shown in ingestion
summaries. `page` is the one-based **physical PDF page**, including cover and
contents pages. Use the viewer's page number, not a printed page label.
The validator rejects extra fields, duplicate JSON keys/IDs/questions/pages,
wrong types, oversized questions, and inconsistent labels. The contract is
[golden.schema.json](golden.schema.json); export it with `--schema`.
The committed baseline provides filled records, with assistant authorship and source
evidence documented separately so the strict schema stays unchanged.

```bash
uv run python -m eval.validate
uv run python -m eval.validate --check-index
```

The first command needs no database or API key. The second verifies every gold
document/page has chunks in the active index before model calls. Wrong hashes,
a different chunk/model profile, and no-text pages fail early.

## Run an evaluation

Configure providers and ingest as described in the main README, then run:

```bash
uv run python -m eval.run --strategy hybrid --k 5 --seed 42
```

`python -m eval.run ...` also works in an activated project environment.
`--golden PATH` and `--output DIRECTORY` override the paths. For a focused check:

```bash
uv run python -m eval.run --strategy vector --question-ids q01,q02,q05,q08,q13,q20,q25,q30
```

IDs must be unique and exist in the unchanged golden file; invalid selections fail
before database/provider setup. Reports explicitly label focused checks, record
selected IDs, and retain the full golden-file digest. New reports also record the
system-prompt SHA-256. Subset aggregates must not replace full-benchmark figures.
`--delay-seconds 15` optionally pauses between questions to pace calls. The
default is zero; this between-question waiting is excluded from latency. Actual
provider attempts are separately paced by typed Gemini settings, including every
retry and each embedding input; this in-request waiting is included in latency. Pacing
does not guarantee provider quota availability or change the seed's limitations. Compose supports:

```bash
docker compose exec backend python -m eval.run --strategy hybrid --k 5
```

Recreate the backend after editing an unmounted golden file so its image includes
it, or bind-mount the evaluation directory with suitable write permissions.
Use host `uv` for automatic Git provenance; minimal runtime images have no Git,
so revision/dirty fields report unknown/null.

Each run saves a Markdown table, full JSON, and per-question JSONL in
`eval/results/`. JSON/JSONL are gitignored because they contain questions, answers,
and quotes. Review Markdown before committing it. Metadata records corpus IDs,
golden digest, index profile, seed, revision, dirty-worktree flag, Python version,
models, thresholds, and safe settings. An allowlist excludes credentials/database
URLs. Keep dependency locks and run against a quiescent index.

The seed controls question order; live models, network timing, and database
caches are not bit-for-bit reproducible. The answer prompt remains versioned in
`backend/app/answering/prompts/system.txt`. No LLM judge is used.

`--fake` explicitly selects both fakes and disables real providers. Fake/mixed
runs are prominently labeled **mechanics only** in reports/filenames. The default
scripted model refuses; it cannot measure semantic quality. CI uses separate
disposable fixtures without external provider calls.

Exit codes: 0 complete, 1 failed attempts or database/output errors, 2 invalid or
empty data/settings or mismatched index. Per-question failures remain in reports
with sanitized codes; they do not silently disappear.

## Metric definitions

| Metric | Definition and denominator |
|---|---|
| Recall@k | Fraction of distinct gold pages found among the first k chunks, macro-averaged over answerable questions |
| MRR@k | Reciprocal rank of the first chunk on any gold page, or zero; macro average over answerable questions |
| Citation validity | Total raw valid / raw proposed quotes before refusal filtering/deduplication; zero proposals is N/A |
| Refusal accuracy | Correct evidence refusals / all unanswerable questions; errors are incorrect, not refusals; no negatives is N/A |
| Latency p50/p95 | Linear interpolation over all end-to-end attempt times, including retrieval, generation, checks, retries, and failures |

k counts chunks, not unique pages. Duplicate chunks cannot inflate recall.
Retrieval failures score zero for recall/MRR; generation failures preserve
retrieval measurements. Error counts and actual class counts are explicit.
Zero denominators never become 100% by convention.

Citation validity uses `AnswerService`'s checks against the exact supplied chunks,
including rejected citations in its counters. It proves provenance, not answer
entailment/completeness. Faithfulness and real-model injection resistance remain
unmeasured. `reference_answer` supports human review; it is not silently scored.

## Compare strategies and chunk sizes

```bash
uv run python scripts/compare_strategies.py --chunk-sizes 200 400 800 --overlap 80 --k 5
```

Profiles must already exist unless you add explicit `--ingest --corpus corpus/`.
That embeds/indexes each configuration using its selected provider and may consume
quota; it never downloads PDFs or falls back to a paid provider. Ingestion remains
idempotent. Overlap must be smaller than every chunk size and is never changed
silently. Bounds are checked before ingestion; document IDs must match across
profiles before evaluation.

`--strategies vector keyword hybrid`, `--seed`, `--delay-seconds`, `--golden`, `--output`, and explicit
`--fake` are available. Every run uses the same golden digest, overlap, k, and
seeded order. Individual records and a combined Markdown table are saved together.
Latency comparisons remain sensitive to caching/network effects; this is a small
sequential baseline, not a controlled load test.

Malformed model output is an error and has no countable citation list. Interpret
citation validity alongside error counts; a high validity ratio alone cannot
establish reliable answer generation. Latency measures the RAG service path,
excluding index preflight, report serialization, and browser-to-API transport.

## Retrieval-only measurement when chat is unavailable

`uv run python -m eval.run --strategy hybrid --k 5 --retrieval-only` measures the
same page rankings on the same golden data and index, without calling or creating
a chat provider. Citation validity and refusal accuracy are **N/A**; latency is
retrieval-only and must not be compared with end-to-end answer latency. Reports
and tables label the mode explicitly. This is a separate explicit experiment,
not a fallback or a substitute for measuring real answers. The workflow's
`retrieval_only` checkbox uses embedding-only preflight and enables this CLI flag.
