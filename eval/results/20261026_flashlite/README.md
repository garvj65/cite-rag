# Frozen Flash-Lite first-run records

Source run: https://github.com/garvj65/cite-rag/actions/runs/40356262638

Artifact 12668032473, verified ZIP SHA-256:
`457278b91438bf209c3c1a5c2bd98872f8d35e6715e7f425f6e56f396fcb04e8`.

The six `answers-*` files preserve the original JSON/Markdown bytes under stable
strategy names. JSON includes all 90 question records, settings, errors and metrics.
They were reviewed as public-corpus outputs before publication; no keys, raw
PDFs, vectors, or private documents are included. Original JSONL rows are redundant
with JSON and remain in the downloadable artifact during its retention period.

| Strategy | Original filename stem |
|---|---|
| vector | `20261026T163101100689Z_configured_vector_k5` |
| keyword | `20261026T163101849580Z_configured_keyword_k5` |
| hybrid | `20261026T164311318217Z_configured_hybrid_k5` |

All aggregates were recomputed and all 45 returned citation quotes matched the
production page/chunk extraction and their per-question retrieved chunk IDs.
Read [the analysis](../20261026_flashlite.md) for denominators, timeout,
false refusals, and the observed q01 semantic wording flag. Labels and the earlier
baseline are unchanged. These are assistant-authored development questions,
not an independently reviewed or held-out benchmark.

[Separate successful live browser validation](browser-validation/README.md) preserves
its own artifact, records and screenshots. It does not replace comparison rows.
