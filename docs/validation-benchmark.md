# Benchmark implementation validation, 2026-10-26

Adapter/retrieval-only implementation revision: `764d21074b42007bb20e1c559a3ec48bebf20c61`.
[Pull-request CI](https://github.com/garvj65/cite-rag/actions/runs/40272841988)
and [push CI](https://github.com/garvj65/cite-rag/actions/runs/40272836444) passed.

| Check | Measured result |
|---|---:|
| Backend/evaluation pytest | 326 passed, including 24 PostgreSQL integration tests |
| Backend app branch-aware coverage | 99.75% |
| Evaluation branch-aware coverage | 99.11% |
| Frontend component tests | 38 passed |
| Browser tests | 5 passed |
| Ruff, format, strict mypy, ESLint, TypeScript | Passed |
| Frontend production build, Docker builds, Compose smoke tests | Passed |

The 30-question assistant-authored baseline contains 25 answerable questions and
five unanswerable questions, including two cases requiring multiple gold pages.
Golden SHA-256: `b1307136fd933bf5b2cf36a1208304e1dfc06dc69f8c939a4a73b95e78224c56`.
Source anchors were checked with the production extractor and page-preserving
400-word/80-word-overlap chunker. Independent human review is still pending.
Reference answers are not sent to the measured model or automatically scored.

Gemini now uses native synchronous batch embeddings and native schema-constrained
chat, behind the existing interfaces. Mocked tests cover separate system/user
content, request schemas and headers, one vector per input, dimensions, finite
nonzero vectors, response order, thought exclusion, split text, malformed and
truncated output, provider blocks, transient retries, and sanitized failure logs.
Tests make no external network calls. Local backend/evaluation checks passed with
302 tests and 24 database tests explicitly skipped; CI verifies the full set.

Authenticated attempts and operational failures are recorded in
[provider attempts](../eval/results/20261026_provider-attempts.md). Gemini 3.8 Flash
returned repeated 503 UNAVAILABLE responses. A separate explicitly selected
Gemini 3.6 Flash preflight succeeded. No model is switched automatically; the
application default remains Gemini 3.8 Flash. The real comparison uses Gemini
Embedding 2 and Gemini 3.6 Flash and must be labeled accordingly.

Gitleaks 8.24.2 scanned all fetched branch history with redaction enabled and
reported no leaks (20 commits containing scanned changes). This is a scanner
result, not proof that every possible credential format is detectable. Actionlint
1.7.7 passed for CI and the explicit evaluation workflow. The key
stays in the existing repository secret and was never read into this workspace.

M5 and public deployment are outside this benchmark release. See the measured
results report for quality numbers and its limitations; software coverage and
source checks alone do not establish semantic quality.

An explicit retrieval-only evaluation mode was added after persistent live chat
rate limits. It never creates/calls an LLM, labels its mode in tables and records,
and reports citation/refusal metrics as N/A. Ranking latency excludes generation.
Tests prove these boundaries on both successful retrievals and failures, and
verify CLI/embedding-only preflight wiring. Full and retrieval-only results must
be reported separately.

All six real result aggregates were recomputed from their raw records. The
artifact ZIP hashes matched GitHub digests, and all 17 returned citations matched
the production extractor/chunker and the question's retrieved chunk IDs. See the
[measured analysis](../eval/results/20261026_gemini_baseline.md) for actual values.
Vector is the final default strategy based on the observed hybrid gate behavior;
the golden labels, prompt, thresholds, and retrieval algorithms remain unchanged.
