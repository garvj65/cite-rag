# M4 implementation validation

Verified on 2026-10-25 against implementation commit
`fb1705448755db8d8f1125200e4e12f21c4b004a`.

[CI run](https://github.com/garvj65/cite-rag/actions/runs/40181853724) passed:

| Check | Measured result |
|---|---|
| Ruff lint and formatting | Passed |
| Strict mypy on app, scripts, and eval | Passed, 46 source files |
| Pytest with PostgreSQL 16/pgvector | 284 passed, 0 skipped |
| PostgreSQL integration tests within that total | 24 passed |
| Combined backend app/evaluation coverage, including branches | 99.53% |
| Separate app and evaluation coverage gates | Both passed the 85% minimum |
| Frontend ESLint and strict TypeScript | Passed |
| Vitest/React Testing Library | 22 passed |
| Playwright browser checks | 3 passed |
| Frontend production build and both Docker images | Passed |
| Full Compose ingestion/search/answer/refusal checks | Passed |
| Six-run comparison: two chunk sizes and three retrieval strategies | Passed on disposable fixture data |
| Evaluation validator/CLI/Markdown/JSON/JSONL inside the runtime image | Passed on disposable fixture data |

Local verification passed 260 tests, explicitly skipped the 24 PostgreSQL tests,
and passed lint, formatting, strict typing, and all frontend checks. CI completed
the database checks afterward. Runtime packaging includes `eval`; its results
directory is writable by the non-root application user.

## Correctness evidence

- Hand-computed page recall and chunk-rank examples cover missing/duplicate pages,
  wrong documents, top-k truncation, and invalid denominators.
- Citation/refusal ratios and interpolated p50/p95 have hand-computed examples.
  Zero denominators return N/A; invalid samples/counts fail explicitly.
- Golden validation covers empty/malformed UTF-8/JSON, duplicate keys/IDs/questions,
  extra fields, wrong types, inconsistent answerability, invalid document hashes,
  physical page bounds, query length, duplicate gold pages, and schema-file drift.
- Real PostgreSQL integration checks reject absent profiles and nonexistent gold
  pages before provider work. All three strategies reach verified scripted answers
  and evidence refusals through the evaluation engine.
- Every question retrieves once. Tests check seeded ordering, retained retrieval
  measurements after generation failure, and failures scoring zero where required.
- Provider/database errors remain sanitized errors and cannot count as correct
  refusals. One valid and one invented citation yields 50% raw citation validity
  even though the whole answer is withheld.
- Provider client reuse, scripted-response reset, cleanup on preflight failure,
  metadata credential exclusion, and optional Git provenance are tested.
- Comparison input bounds are checked before ingestion; different document sets
  are rejected. Ingestion is explicit, overlap is preserved, and raw records plus
  a combined Markdown table are written. Atomic output failures preserve an
  existing file and remove temporary files.

## Boundaries and remaining inputs

The tracked `eval/golden.jsonl` is empty. The user must author the intended
questions, answerability labels, and gold document/pages. **No real user-golden
quality benchmark has run.** No user golden questions, gold answers, semantic-quality
results, or real-model faithfulness scores have been invented.

Tests use deterministic embeddings, scripted responses, local PostgreSQL, and
mocked provider HTTP. CI's transient labels refer only to its generated smoke PDF
and never populate the user's golden file. Browser tests intercept API responses.
No authenticated Gemini/OpenAI call was made.

The seed fixes question order, not live model output, caches, or latency. Citation
validity establishes quote provenance, not entailment. No LLM judge is used.
Experiments require a quiescent index. Minimal runtime images lack Git, so their
Git provenance is unknown; host runs record the checked-out revision/dirty flag.

The two configuration findings are non-blocking with unchanged defaults and are
documented in [configuration-review.md](configuration-review.md); they are not
silently marked fixed. The requested UI/UX redesign is deferred. The free-tier VM
deployment runbook is documented but has not been live-deployed or ARM-tested.

The evaluation implementation is ready for review. The project's full definition
of done still requires user-authored golden data and real measured results in the
README; test coverage and fake-fixture scores do not substitute for that work.
