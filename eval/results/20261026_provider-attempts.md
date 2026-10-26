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
provider fallback was introduced. Follow-up native-API results are pending.
