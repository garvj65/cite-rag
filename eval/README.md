# Evaluate CiteRAG

The harness is implemented. **The user writes the golden questions and answers.**
`golden.jsonl` is intentionally empty; no semantic benchmark has been run and no
quality scores have been invented. Empty data fails validation. Test/CI questions
are separate synthetic fixtures, never starter NIST golden questions.

## Author the golden file

Write one JSON object per line in `eval/golden.jsonl`. Aim for the planned
25 answerable and 5 unanswerable questions; a smaller first dataset is valid.

| Field | Required | Meaning |
|---|---|---|
| `id` | Yes | Unique, nonempty stable identifier |
| `question` | Yes | Your question, within the backend query-length setting |
| `answerable` | Yes | Boolean determined by reading the corpus |
| `gold_pages` | Yes | Expected pages as objects with `doc_id` and `page`; empty for negatives |
| `reference_answer` | No | Your human reference answer for answerable rows; not automatically scored |

`doc_id` is the lowercase SHA-256 of original PDF bytes, shown in ingestion
summaries. `page` is the one-based **physical PDF page**, including cover and
contents pages. Use the viewer's page number, not a printed page label.
The validator rejects extra fields, duplicate JSON keys/IDs/questions/pages,
wrong types, oversized questions, and inconsistent labels. The contract is
[golden.schema.json](golden.schema.json); export it with `--schema`.
No filled example is supplied, to avoid inventing your questions or answers.

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
`--golden PATH` and `--output DIRECTORY` override the paths. Compose supports:

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

`--strategies vector keyword hybrid`, `--seed`, `--golden`, `--output`, and explicit
`--fake` are available. Every run uses the same golden digest, overlap, k, and
seeded order. Individual records and a combined Markdown table are saved together.
Latency comparisons remain sensitive to caching/network effects; this is a small
sequential baseline, not a controlled load test.
