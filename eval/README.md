# Evaluate CiteRAG

The harness is implemented. At the user's explicit request on 2026-10-26,
`golden.jsonl` now contains an **assistant-authored pilot: four answerable questions
and one unanswerable question**. Read [the answer key and evidence review](golden-review.md).
Source/hash/page/chunk checks passed; independent human review and a real-provider
run remain pending. No quality scores have been invented. Test/CI questions remain
separate synthetic fixtures. Empty datasets still fail validation.

For a browser-only run, follow [the evaluation handoff](../docs/evaluation-handoff.md).
The [corpus reference](../docs/corpus-reference.md) gives verified document hashes
and physical page counts without requiring local ingestion.

## Author the golden file

Review the pilot, then add one JSON object per line in `eval/golden.jsonl`.
Aim for the planned 25 answerable and 5 unanswerable questions; a smaller first dataset is valid.

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
The committed pilot provides filled records, with assistant authorship and source
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
`--golden PATH` and `--output DIRECTORY` override the paths.
`--delay-seconds 15` optionally pauses between questions to pace calls. The
default is zero; intentional waiting is excluded from measured latency. Pacing
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
