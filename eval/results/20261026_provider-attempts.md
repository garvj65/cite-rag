# Real-provider attempts, 2026-10-26

## Initial pilot ingestion

[Run 40267443361](https://github.com/garvj65/cite-rag/actions/runs/40267443361)
used revision `ed11189208cf132f338327ca8aa86c30654a6531` and the five-question
pilot digest `31bd35e6e31ced96902a4408231e33c88630883ef5f0bb8021609a7cb173e385`.
Gemini models were explicitly selected; the existing Actions repository secret
was used without revealing its value.

Both PDFs failed with the sanitized reason `embedding_failed`: 0 documents,
0 pages, and 0 chunks were indexed; 2 files failed. The run stopped before any
question was evaluated. No recall, MRR, citation-validity, refusal-accuracy, or
answer-latency measurement was produced. These are operational ingestion counts,
not semantic-quality scores. No failure was counted as a correct refusal.

The initial adapter errors did not expose the provider HTTP status. A small,
explicit provider preflight was added to report safe numeric HTTP statuses and
allowlisted codes before retrying corpus ingestion. It never prints the secret,
request/response bodies, or generated content. Further attempts are recorded
below when their results are available.

## Credential-safe preflight

[Run 40268490218](https://github.com/garvj65/cite-rag/actions/runs/40268490218)
used revision `d16d8f85dfdf1908eb585eb34c59dade3ccd6892`. The embedding
request returned HTTP 200 but failed the adapter's vector-response contract.
Chat returned HTTP 503 on two observed HTTP attempts and failed after bounded
retries. The run stopped before corpus ingestion and evaluated zero questions.
This is provider-integration evidence, not a retrieval/answer-quality result.

The Gemini embedding adapter was changed to Google's native synchronous
`batchEmbedContents` endpoint, requesting 1536 dimensions separately for each
input. It checks count, dimensionality, finite numeric values, and nonzero vectors.
OpenAI remains explicitly selectable through its existing adapter. No model or
provider fallback was introduced.

## Native embedding verification

[Run 40269756099](https://github.com/garvj65/cite-rag/actions/runs/40269756099)
used revision `573358bd56a5f2a04569fdad94e4f5f1a57b4ab9` and the expanded
30-question dataset. Native embedding preflight passed: HTTP 200, one embedding,
1536 dimensions, and all vector checks passed. Chat still returned HTTP 503 on
two observed HTTP attempts and ended with a sanitized timeout after bounded
retries. The workflow stopped before ingestion; zero questions were evaluated.

Gemini chat was then updated to its documented native `generateContent` endpoint
with `generationConfig.responseFormat.text` JSON schema. This is an explicit
adapter implementation change, with the same configured model and no automatic
fallback. Tests cover the request contract, split text, thought exclusion,
malformed/truncated responses, provider blocks, and transient retries. The
[official REST example](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)
and [API reference](https://ai.google.dev/api/generate-content) define the contract.
A follow-up real check is required before claiming chat or quality measurements.

## Native chat availability

[Run 40270187206](https://github.com/garvj65/cite-rag/actions/runs/40270187206)
used revision `b72dc6569430e6adc0ee1855118b2296b4519448`. Embedding preflight
passed again (HTTP 200, 1 x 1536). Native Gemini 3.8 Flash chat returned HTTP 503
with the allowlisted provider status `UNAVAILABLE` on all three attempts. No
corpus was ingested and no questions were evaluated. This confirms a live chat
availability blocker across both native and compatibility endpoints; it does
not establish a key/account/billing root cause.

A separate Gemini 3.6 Flash experiment is selectable explicitly in the workflow;
the app default and existing evidence remain unchanged. No automatic or paid
provider fallback is used.

## Gemini 3.6 Flash preflight and partial ingestion

[Run 40270698621](https://github.com/garvj65/cite-rag/actions/runs/40270698621)
used revision `b1b143a30f0cbe6679e2f1e20a40f21761c19db2`, explicitly selecting
Gemini 3.6 Flash. Both embedding and schema-constrained chat preflights passed
with HTTP 200. The RMF PDF indexed successfully: 48 pages and 66 chunks. GenAI
ingestion failed with `embedding_failed`; zero questions were evaluated. The
failed request status was not logged, so quota or availability is not yet proven
as the cause.

Provider failures now log only numeric HTTP status at WARNING, without URL,
headers, messages, or document text. The explicit benchmark uses existing
backoff settings at 30/60 seconds (three attempts), capped at 60 seconds, to
allow more recovery time. Application defaults remain unchanged.

## Successful full corpus ingestion

[Run 40271174202](https://github.com/garvj65/cite-rag/actions/runs/40271174202)
uses revision `b2ed89955a1f5c6624bbd83fa821fe7855e75ba6` and explicitly
selected Gemini 3.6 Flash with Gemini Embedding 2. Both preflights passed.
Ingestion logged two HTTP 429 rate-limit responses and recovered with the
configured 30/60-second retry delays. Both PDFs indexed successfully: 2 documents,
112 pages, 149 chunks, 0 skipped files, and 0 failed files. These operational
counts are distinct from quality metrics. The three-strategy benchmark follows
in the same disposable database; its completed results must be reported separately.

## Completed benchmark records

Run 40271174202 completed all three 30-question end-to-end passes. It exited with
failure: vector had 14 generation failures, hybrid had 2, and keyword had none.
The workflow was not cancelled; it completed while chat/browser controls were
unavailable. The separate explicitly retrieval-only run
[40272916763](https://github.com/garvj65/cite-rag/actions/runs/40272916763) completed
all three strategies with zero errors after the earlier run released the
concurrency slot. No LLM was called in that second run.

[Full measured results and preserved raw records](20261026_gemini_baseline.md)
include the failures, refusal behavior, latencies, exact model IDs, dataset digest,
and immutable revisions. These results supersede earlier pending-quality notes
without converting any failed request into a successful refusal.
