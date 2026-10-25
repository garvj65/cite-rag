# M3 validation record

Verified on 2026-10-25 against implementation commit
`9e94c32abe7d67fef27bcc8b40206d1d6257caf9`.

[CI run](https://github.com/garvj65/cite-rag/actions/runs/40173531346) passed:

| Check | Measured result |
|---|---|
| Ruff lint and formatting | Passed |
| Strict mypy on application and scripts | Passed, 36 source files |
| Pytest with PostgreSQL 16/pgvector | 207 passed, 0 skipped |
| PostgreSQL integration tests within that total | 19 passed |
| Backend application coverage, including branches | 99.71% |
| Frontend ESLint and strict TypeScript | Passed |
| Vitest and React Testing Library | 22 passed |
| Vite production build | Passed |
| Backend and frontend Docker builds | Passed |
| Compose configuration and complete startup | Passed |
| Compose ingestion and duplicate skipping | Passed |
| All three retrieval strategies through HTTP | Passed |
| Verified answers and evidence refusal through the frontend API proxy | Passed |
| Playwright desktop/mobile browser checks | 3 passed |

## Behavior checked

- Empty and weak retrieval return a fixed refusal before constructing a chat
  client. Independent score gates cover vector, keyword, and hybrid strategies.
- Bounded numbered JSON passages preserve exact document/page identities. Whole
  chunks are included; excluded or weak chunks cannot validate a citation.
- Strict output parsing rejects malformed JSON, duplicate/unknown fields,
  incorrect types, excessive nesting, invalid Unicode, truncated responses, and
  configured size/count violations.
- Quotes must occur within one supplied chunk on the stated document and page,
  normalizing whitespace only. Wrong documents/pages, invented text, case changes,
  ellipses, empty quotes, cross-chunk fragments, and missing citations fail.
- Any invalid citation suppresses the whole answer. Unsupported model answers
  become fixed refusals. Raw proposed/valid counts survive refusal filtering and
  deduplication, so later citation evaluation need not measure only released quotes.
- Provider configuration errors, timeouts, retryable/permanent failures, and bad
  output produce sanitized error statuses, distinct from document refusals.
- A document containing injected instructions stays in the user message's JSON
  data. Scripted forged citations are rejected; no tool or command execution exists.
- The UI covers empty, loading, supported, refused, and error states, stale-answer
  clearing, cancellation on unmount, unsafe URLs/HTML, and malformed API contracts.
- The actual Compose deployment ingests an offline PDF twice and checks search
  and verified answers for all three strategies through HTTP. nginx serves the
  built frontend and proxies `/api/ask`; unsupported keyword evidence refuses.
- Browser checks exercise citation expansion, refusals without citation cards,
  and a mobile error state without horizontal overflow. The README screenshot
  comes from the real production build; it contains no invented corpus answer.

Local checks passed 188 backend tests with 19 database tests explicitly skipped
and 96.77% coverage; CI completed all 19 database checks afterward.

## Measurement boundaries

Python tests block external sockets; all provider HTTP is mocked. PostgreSQL
integration uses a local disposable test service. Compose smoke checks select
both fake providers explicitly. Browser tests intercept answer requests and block
non-loopback requests. Installing dependencies/browser binaries is setup, not a
provider call performed by a test.

No authenticated Gemini/OpenAI call was made. Real credentials, account quotas,
and live model/schema compatibility remain unverified. Scripted responses are
labeled in the UI and are not a substitute for model reasoning or golden data.

Quote matching establishes provenance, not entailment of every answer claim.
Scripted injection tests do not establish live-model prompt-injection immunity.
Evidence thresholds are provisional and uncalibrated. M4 must measure semantic
retrieval, faithfulness/refusal behavior, and latency using user-authored golden
data. No golden questions, answers, or model-quality metrics were invented.
