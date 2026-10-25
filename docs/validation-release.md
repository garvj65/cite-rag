# Release-readiness validation, 2026-10-25

Implementation revision: [`5b6bb78`](https://github.com/garvj65/cite-rag/commit/5b6bb78fd4e4fc492665b4850d51f6d37c80eb2f).
[PR #5](https://github.com/garvj65/cite-rag/pull/5) contains the release work.
Both [pull-request CI](https://github.com/garvj65/cite-rag/actions/runs/40202787998)
and [push CI](https://github.com/garvj65/cite-rag/actions/runs/40202763412) passed.
These are measured software checks, not a semantic-quality benchmark.

| Check | Measured result |
|---|---:|
| Backend/evaluation pytest | 294 passed, no skips in CI |
| PostgreSQL 16/pgvector integration tests included above | 24 passed |
| Backend application branch-aware coverage | 99.74% |
| Evaluation branch-aware coverage | 99.08% |
| Combined app/evaluation coverage | 99.56% |
| Vitest/React Testing Library | 38 passed |
| Playwright Chromium | 5 passed |
| Ruff, formatting, strict mypy, ESLint, TypeScript | Passed |
| Production frontend and both Docker images | Built successfully |
| Actual Compose stack and nginx configuration | Passed |

## Behaviors verified

- Existing PDF edge cases, atomic/idempotent ingestion, vector/FTS/RRF retrieval,
  strict answer JSON, exact chunk/quote verification, refusals, and injected
  document fixtures remain covered. Provider HTTP is mocked; Python tests block
  external sockets. PostgreSQL integration uses a disposable local service.
- A blocked-worker test proves `/ask` and `/search` return a sanitized deadline
  504 before the worker finishes and leave its resource cleanup to that worker.
  Provider phase timeout/backoff respect the remaining API budget. Invalid
  deadline/proxy settings fail early. An expired context cannot begin work.
- The public configuration allowlist excludes credentials and connection details.
  Unit/component tests cover Unicode counting and changed limits. CI uses a real
  173-character backend limit, keyword default, and k=3; nginx and Chromium both
  read the actual public configuration. No operational UI limit is hardcoded.
- CI renders a 12-second nginx timeout against a five-second API deadline and
  checks the generated config with `nginx -t`. The same proxy handles all three
  retrieval strategies, verified cited answers, and evidence refusals.
- Browser fixtures cover supported answers, expandable exact quotes, explicit
  scripted labels, refusals, errors on mobile, and strategy/k request bodies.
  Non-loopback browser requests are blocked. Local desktop and 390-pixel mobile
  screenshots were inspected; the empty-workspace screenshot is committed with
  no fabricated corpus answers or counts.
- Evaluation pacing is tested with a hand-controlled clock: one pause between
  two questions, excluded from each question's latency. Existing metric and
  strategy/chunk comparison tests remain passing. The packaged evaluator writes
  Markdown/JSON/JSONL using separate disposable CI questions, never user gold.

## Additional local checks

Actionlint 1.7.7 passed for normal CI and the manual evaluation workflow. Gitleaks
8.24.2 scanned all 13 fetched commits including the release implementation with
redaction enabled and reported no leaks. This is a scanner result, not proof
that every possible secret format is detectable. Dependency locks validate;
no model/provider calls were made by these tests.

Locally, 270 backend/evaluation tests passed with 24 database tests explicitly
skipped because no local PostgreSQL service was configured; app coverage was
96.42%. Four browser tests passed against a static production build; the fifth
requires the actual Compose service and passed in CI. CI is authoritative for
full-stack/database coverage above.

## Completion boundary and review

M1–M3 functionality and M4 harness code are implemented. The requested UI redesign,
shared settings, response/proxy deadlines, screenshot, deployment instructions,
learning guide, and explicit browser-run evaluation handoff are delivered here.

The project's full definition of done remains **open**: `eval/golden.jsonl` is
empty, no Gemini key is configured in this workspace, authenticated model access
has not been exercised, and real recall/MRR/citation/refusal/latency numbers are
not yet available. The README keeps these cells pending. The user authors the
questions/pages; [the handoff](evaluation-handoff.md) explains the repository
secret and manual workflow. That real workflow was statically checked but has
not been executed. No faithfulness judge or semantic entailment claim is added.

No public deployment or M5 memory/tool loop is included. M5 remains conditional on
completed real M4 measurement. In-flight synchronous work can finish after an API
response deadline; the deadline does not cancel remote work or control billing.
Review the workspace on desktop/mobile, citation expansion/refusal states, shared
configuration behavior, deadline cleanup, and manual evaluation opt-in before
approving the release merge. `AGENTS.md` requires approval before merging.
