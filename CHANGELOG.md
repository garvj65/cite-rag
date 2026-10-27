# Change history

Release summaries live here; code and deleted milestone reports remain available
in Git history. Measured benchmark artifacts are preserved under `eval/results/`
and are never rewritten to reflect a later fix. No Git history is rewritten.

## Final cleanup — 2026-10-27

- Preserve obligation, uncertainty, conditions, exceptions, and negation in the
  answer prompt after q01 changed source “should” into “must.” Exact quote
  verification remains unchanged and does not establish semantic faithfulness.
- Add focused selection of existing golden IDs, visibly label subset reports,
  and record the system-prompt digest. Keep full golden-file identity unchanged.
- Reuse compatible public-corpus database snapshots in manual evaluations. Run
  every selected strategy and optional browser check against one index. Cache
  Chromium downloads; browser checks are opt-in. Upload only this run's outputs.
- Consolidate seven milestone/validation reports and overlapping configuration,
  deployment, and browser handoff instructions into the README, operations guide,
  evaluation guide, and this history. Keep source artifacts and learning material.
- Record the user's completed answer-key review and deliberate retention of q30
  as an ambiguous expected-refusal edge case. No question, answer, or label changed.
- Focused real-provider and final CI results: pending execution for this revision.

## Budget model and hybrid correction — 2026-10-26

[PR #7](https://github.com/garvj65/cite-rag/pull/7), merged as `14ffcca`.
Explicit Flash-Lite/Embedding 2 configuration, bounded process-local attempt/input
pacing, and hybrid evidence gating by original cosine/FTS scores instead of RRF.
Original all-strategy measurements retain vector's timeout, hybrid's zero-error
21/25 supported positives, all refusals, and observed q01 wording drift.
[Results and raw records](eval/results/20261026_flashlite.md) include the separate
real UI/citation/refusal captures. Both model selection and prompt revision are
part of provenance; this did not establish independently judged answer accuracy.
[Post-merge CI](https://github.com/garvj65/cite-rag/actions/runs/40365696888):
341 backend/evaluation tests, 99.77% app coverage, 38 component and five browser tests.
Gitleaks 8.24.2 found no leaks in all fetched history at the final PR head; this is
a scanner result, not a guarantee for every possible secret format.

## Golden baseline and real adapters — 2026-10-26

[PR #6](https://github.com/garvj65/cite-rag/pull/6), merged as `e22530d`.
Native Gemini batch embedding and schema-constrained generation, 30 source-checked
assistant-authored questions/key, provider preflight, retrieval-only measurement,
and retained quota/provider failures. [CI](https://github.com/garvj65/cite-rag/actions/runs/40272841988):
326 backend/evaluation tests, 99.75% app coverage. [Baseline](eval/results/20261026_gemini_baseline.md).

## Research workspace and delivery — 2026-10-25

[PR #5](https://github.com/garvj65/cite-rag/pull/5), merged as `bb84986`.
Responsive UI redesign, backend-owned client limits, API/proxy deadlines,
Docker/Compose delivery, deployment/learning guidance, and manual real evaluation.
[CI](https://github.com/garvj65/cite-rag/actions/runs/40202787998):
294 backend/evaluation tests, 99.74% app coverage, 38 component and five browser tests.

## Core milestones

| Milestone | Delivered | PR | Original full CI |
|---|---|---|---|
| M4 | Golden schema, metric functions, evaluator, strategy/chunk comparison | [#4](https://github.com/garvj65/cite-rag/pull/4) | [284 backend/eval tests](https://github.com/garvj65/cite-rag/actions/runs/40181853724) |
| M3 | Strict cited answers, quote verification/refusal, injection fixtures, React UI | [#3](https://github.com/garvj65/cite-rag/pull/3) | [207 backend tests](https://github.com/garvj65/cite-rag/actions/runs/40173531346) |
| M2 | Vector, PostgreSQL FTS, and RRF retrieval through one interface | [#2](https://github.com/garvj65/cite-rag/pull/2) | [143 backend tests](https://github.com/garvj65/cite-rag/actions/runs/40163245109) |
| M1 | Manifest downloader, per-page extraction/chunking, atomic idempotent ingestion | [#1](https://github.com/garvj65/cite-rag/pull/1) | [83 backend tests](https://github.com/garvj65/cite-rag/actions/runs/40087791508) |

All ordinary CI provider calls use deterministic fakes/mocks. Test totals describe
those exact historical revisions. M5 memory/tool use and public deployment have
not been implemented as part of this release.
