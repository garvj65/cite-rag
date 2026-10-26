# Measured Gemini baseline, 2026-10-26

The baseline contains **30 assistant-authored questions: 25 answerable and 5
unanswerable** over two public NIST PDFs (112 physical pages, 149 chunks).
Chunk size/overlap: 400/80 words; k=5 chunks; seed=42. Golden SHA-256:
`b1307136fd933bf5b2cf36a1208304e1dfc06dc69f8c939a4a73b95e78224c56`.
Index profile: `4a3e52273c1fcc3f62adc29a0d5a10b20b4b5757447d1fb87e8bf333686da91d`.
Independent human label review is pending; this is a small baseline, not a held-out
or independently validated benchmark. Reference answers are not sent to the model
or automatically scored. No LLM judge or faithfulness score is used.

## Real retrieval comparison

[Run 40272916763](https://github.com/garvj65/cite-rag/actions/runs/40272916763),
revision `764d21074b42007bb20e1c559a3ec48bebf20c61`, used **Gemini Embedding 2**
and explicitly skipped all chat calls. Each strategy evaluated all 30 questions
without errors. Recall and MRR average over 25 answerable questions. The five
negatives have no gold pages and are excluded from those averages. Latency is
retrieval-only; its two-second pauses are excluded. Answer metrics are N/A.

| Mode | Strategy | Chunk words | k | Questions | Errors | Recall@k | MRR@k | Citation validity | Refusal accuracy | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| retrieval | vector | 400 | 5 | 30 | 0 | 0.8800 | 0.6747 | N/A | N/A | 221.6401 | 294.2316 |
| retrieval | keyword | 400 | 5 | 30 | 0 | 0.0600 | 0.0800 | N/A | N/A | 4.6704 | 5.7606 |
| retrieval | hybrid | 400 | 5 | 30 | 0 | 0.8800 | 0.7047 | N/A | N/A | 221.9991 | 276.0097 |

## Real end-to-end attempt, including failures

[Run 40271174202](https://github.com/garvj65/cite-rag/actions/runs/40271174202),
revision `b2ed89955a1f5c6624bbd83fa821fe7855e75ba6`, used **Gemini Embedding 2
and Gemini 3.6 Flash**. Gemini 3.8 Flash had returned repeated 503 UNAVAILABLE
responses in earlier checks; 3.6 was selected explicitly, without changing the
app's chat-model default or adding a fallback. Both preflights passed. Ingestion
recovered from HTTP 429 responses using 30/60-second backoff and indexed both PDFs.

All three strategies completed 30 question records. The workflow correctly exited
with failure because provider errors occurred. These are the actual measured
results, not a successful, quota-free answer benchmark. Latency includes
retrieval, generation when attempted, validation, and retries, including failures;
15-second pauses between questions are excluded.

| Mode | Strategy | Chunk words | k | Questions | Errors | Recall@k | MRR@k | Citation validity | Refusal accuracy | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| end-to-end | vector | 400 | 5 | 30 | 14 | 0.8800 | 0.6747 | 0.9474 | 0.4000 | 76601.8351 | 95359.1988 |
| end-to-end | keyword | 400 | 5 | 30 | 0 | 0.0600 | 0.0800 | N/A | 1.0000 | 3.6061 | 4.7374 |
| end-to-end | hybrid | 400 | 5 | 30 | 2 | 0.8800 | 0.7047 | N/A | 1.0000 | 288.2691 | 50079.3999 |

## Interpretation and remaining gaps

- Vector and hybrid found 88% of labeled gold pages on average. Hybrid's MRR was
  0.7047 versus vector's 0.6747; this small dataset does not establish a general
  advantage. Keyword's strict term matching performed poorly on these questions.
- Vector had **14 generation failures**, **12 supported answerable responses**,
  and **1 refused answerable response** (`q16`, invalid citation). Its raw quote
  verification was **18/19 = 94.74%**. The invalid proposal caused the whole answer
  to be refused. Its returned citations all passed the independent source check.
- Of the five vector negatives, two were correct refusals, two were provider
  failures, and `q30` returned a cited explanation of NIST's non-prescriptive
  framework with `supported=true`. The frozen label expects refusal to the
  requested exact budget, so the reported score is **2/5 = 40%**. This is a
  false-premise/label interpretation case for independent review; the response
  did not invent a dollar amount. The label was not changed after seeing output.
- Keyword refused all 25 positives and all five negatives (28 empty retrievals,
  2 weak retrievals). Hybrid refused all 23 non-error positives and all five
  negatives via its weak-evidence gate, with 2 generation failures. Their 100%
  negative refusal scores do **not** establish useful answering behavior.
- With RRF constant 60, a first-ranked chunk from only one ranking scores
  `1/61`, below the provisional hybrid answer threshold 0.02. This explains why
  strong ranking recall can coexist with mostly refused answers. Thresholds have
  not been lowered against this same golden set. **Vector is now the default
  strategy**; hybrid remains selectable and its gate needs separate calibration.
- Provider HTTP 429/503 responses limit the end-to-end comparison. Do not use its
  latencies to compare normal serving speed or claim stable model availability.
  An account-specific daily-quota root cause was not established by these logs.
- Quote occurrence measures provenance, not entailment, completeness, or semantic
  answer accuracy. No faithfulness or prompt-injection-resistance claim follows
  from these numbers. Current labels, alternative supporting pages, refusal
  boundaries, and thresholds need independent review and a fresh held-out set.

## Records and reproduction

[Six frozen JSON/Markdown reports, checksums, and artifact provenance](20261026/README.md)
retain all 180 question records. The original JSON bytes and dirty flags are
preserved. Future reports remain outside this archive. Application code changes
in this release select vector as the default only; the measured strategies were
all explicit, and retrieval/prompt/threshold algorithms were not tuned after the
run. Full software checks are in [benchmark validation](../../docs/validation-benchmark.md).

To repeat without a local build, use the manual workflow described in the
[browser handoff](../../docs/evaluation-handoff.md). Keep the same corpus hashes,
chunk settings, seed, k, and explicit model selection. Turn retrieval-only off
for an answer run and inspect actual errors/denominators. A fixed seed does not
make live providers, caches, or latency bit-for-bit reproducible. No new real
calls were made solely to hide a failed question or improve these scores.
