# Quality pass validation, 2026-10-26

Implementation revision: `a0e83ef53f2462e166deb2aecee98bda7ec4c17e`.

This pass changes the explicit budget chat model to Gemini 3.5 Flash-Lite,
retains Gemini Embedding 2 and vector retrieval, and corrects the hybrid answer
gate. RRF still determines rank; the existing cosine (0.35) or FTS (0.05)
component threshold determines passage eligibility. Neither threshold was tuned
on the frozen golden answers. Search results and evaluation records preserve
component scores for inspection. The retired RRF threshold is no longer used.

Gemini attempts are paced before every HTTP call, including retries. Chat costs
one unit; synchronous embedding batches conservatively cost their input count.
A shared process-local limiter spaces attempts and enforces a rolling-minute
budget, honoring API deadlines. Defaults are 12 chat attempts/minute and 90
embedding inputs/minute; the workflow explicitly uses 4 chat attempts/minute for
3.6/3.8 Flash. This is not daily/token quota enforcement or distributed limiting.
Model selection remains explicit, with no billing changes or provider fallback.

Local verification passed: Ruff and formatting, strict mypy on 50 source files,
317 backend/evaluation tests, 38 frontend tests, ESLint, TypeScript, production
frontend build, Actionlint 1.7.7, golden schema and diff whitespace checks.
24 PostgreSQL integration tests were skipped locally and are exercised in CI.
Local app branch-aware coverage was 96.83%; combined app/eval coverage 96.67%.
A stale mypy SQLite cache was replaced; the normal type-check command then passed.
No dependency lock or application type-check setting was relaxed.

New regressions cover a strong vector-only hybrid hit with low RRF, keyword-only
support, high-RRF weak evidence, missing component scores, prompt passage order,
component-score merging, actual retry pacing, weighted rolling embedding budgets,
concurrent clients, separate endpoints, batch bounds, and deadline exhaustion.
All test provider HTTP is mocked and pacing uses a fake clock without real sleeps.
The explicit browser evaluation script is outside normal offline tests and
requires both real-provider opt-in and an explicit command-line authorization.

The existing golden file and all prior reports are frozen. Independent human
label review, q30's false-premise policy, held-out validation, and semantic
faithfulness remain open. Source quote validity alone is not answer accuracy.

Full [push CI](https://github.com/garvj65/cite-rag/actions/runs/40355960663)
and [PR CI](https://github.com/garvj65/cite-rag/actions/runs/40356004333) passed on the implementation revision: **341 backend/evaluation tests**, including
24 PostgreSQL tests; **99.77% backend app coverage** and **99.11% eval coverage**;
38 frontend tests; five Chromium tests; lint/format/strict typing; production
frontend and Docker builds; real Compose ingestion/idempotency/search/cited-answer
and refusal smoke checks; nondefault settings and nginx proxy verification.
The CI checks use deterministic fakes, not real quality measurements.

Gitleaks 8.24.2 scanned all fetched history at the implementation revision with
redaction: 23 commits containing changes, about 1.15 MB, no leaks detected.
The Actions secret was neither read nor copied into the workspace.

The PR CI runner took extra time downloading Ubuntu browser/font dependencies;
it recovered and completed successfully. No CI job or benchmark was cancelled.

Workflow follow-up revision: `15866de4c736a5e36379f1dcd8e3e7b8d2ef9d02`.
A retained question error must not suppress the optional browser check. Its guards
now require successful ingestion and browser setup and skip on cancellation.
Provider preflight/ingestion failures still prevent browser calls; retrieval-only
mode still makes no chat calls. Actionlint and diff whitespace checks passed.
This changes workflow conditions only; measured application code is unchanged.

Both [push CI](https://github.com/garvj65/cite-rag/actions/runs/40360387750)
and [PR CI](https://github.com/garvj65/cite-rag/actions/runs/40360395009) passed
on the workflow follow-up revision. The full application suite and Compose/browser
checks remain green. The live all-strategy run remains pinned to the first
implementation revision; a separate browser verification run uses the follow-up.

The [Flash-Lite comparison](../eval/results/20261026_flashlite.md) completed all
90 question attempts. The workflow failed honestly on vector q13's provider
timeout. Hybrid had zero errors, 21/25 supported positives and five correct
negative refusals. Keyword refused all 30 questions. All three aggregates were
recomputed from raw rows; all 45 returned quotes were rechecked against exact
production chunks and retrieved IDs. A valid quote still permits semantic drift:
hybrid q01 strengthens source “should” to “must.” Independent semantic/label review
and held-out validation remain pending. No prompt, threshold or label was tuned.

[The explicit live browser run](https://github.com/garvj65/cite-rag/actions/runs/40360595059)
passed using the unchanged application and prompt. Chromium submitted q01 and q05
through the real FastAPI/Vite UI, expanded a source-matched citation, checked its
PDF page link, and displayed a citation-free model refusal. Both responses were
real model outputs. One returned quote was separately source-checked. JSON and
exact screenshots are archived; the README now uses the real answer capture.
The browser answer also contains the observed “should”/“must” wording issue, which
is documented rather than edited away. The separate keyword operational recheck
is not combined with or substituted for the three-strategy comparison.
