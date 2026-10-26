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
