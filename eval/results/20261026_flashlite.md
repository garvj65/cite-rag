# Gemini Flash-Lite quality pass, 2026-10-26

[Complete first-run records](https://github.com/garvj65/cite-rag/actions/runs/40356262638) cover all three strategies: 30 questions each, 25 answerable and five negative. The workflow **exited with failure** because vector q13 exhausted provider timeouts. Hybrid and keyword completed without errors. No strategy was cancelled, selectively rerun, or substituted in this comparison.

Gemini Embedding 2 and explicit Gemini 3.5 Flash-Lite; two NIST PDFs, 112 physical pages, 149 chunks; 400-word chunks, 80-word overlap, k=5, seed=42. These are end-to-end measurements on the existing assistant-authored development baseline, not held-out or independently reviewed quality scores.

| Strategy | Recall@5 | MRR@5 | Raw quote validity | Correct negative refusals | Supported positives / 25 | Errors / 30 | p50 / p95 seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Vector | 88.00% | 0.6747 | 24/27 (88.89%) | 5/5 (100%) | 19 | 1 | 22.3214 / 133.3919 |
| Keyword | 6.00% | 0.0800 | N/A (0 proposals) | 5/5 (100%) | 0 | 0 | 0.0030 / 0.0042 |
| Hybrid | 88.00% | 0.7047 | 25/27 (92.59%) | 5/5 (100%) | 21 | 0 | 21.2743 / 58.1102 |

Supported positives count answers accepted by the application; they are **not a measured correctness or faithfulness rate**. Raw quote validity counts proposals before refusals/deduplication. All **45 returned citations** (21 vector, 24 hybrid) were independently rechecked against the production extractor/chunker and the question's retrieved chunk IDs. All matched. Five invalid proposed quotes caused five complete answer refusals; valid partner citations from those refused answers were also withheld.

Keyword refused every question: 28 empty retrievals and two weak retrievals. Its 100% negative-refusal figure and low latency do not establish useful answering. No chat calls were made for those 30 keyword questions.

Hybrid now uses the existing cosine/FTS evidence gates, preserving RRF only for rank. For example q01's first hit has RRF 0.0163934, vector similarity 0.8247718, and no keyword component. The old RRF threshold of 0.02 would have refused it; the corrected gate admits its strong vector evidence. No numeric component threshold, prompt, or golden label was tuned. The chat model and pacing also changed from the prior baseline, so improvements cannot be attributed to a single variable in isolation. These are single sequential trials; output/availability differences do not establish a causal strategy advantage. Vector remains the explicitly approved app default; this one small development run does not establish a universally best strategy.

## Failure and refusal review

| Question | Vector | Hybrid | Evidence observation |
|---|---|---|---|
| q06 | Invalid citation; withheld | Invalid citation; withheld | Gold page retrieved in both cases |
| q12 | Invalid citation; withheld | Invalid citation; withheld | Gold page retrieved; a valid partner quote is also withheld |
| q13 | Provider timeout; no answer | Supported | Vector retrieved its gold page first; generation failed after 180.42 seconds including retries/backoff |
| q16 | Invalid citation; withheld | Supported | Vector found one of two listed gold pages |
| q21 | Model unsupported | Model unsupported | Listed gold page missing from top five |
| q26 | Model unsupported | Model unsupported | One of two listed gold pages retrieved |

The vector timeout is an operational failure, not a correct refusal. Logs also retain one HTTP 503 during the measured stage; they do not identify a definitive account/capacity root cause for the timeout. No 429 was logged in this run. Larger daily quota and local pacing do not guarantee provider capacity or eliminate outages. The previous baseline remains [unchanged](20261026_gemini_baseline.md).

## Semantic review remains open

An assistant inspection found a concrete limitation in hybrid q01: the answer strengthens the source's recommendation from “should” to “must,” although its quote matches exactly. This is a wording/faithfulness review flag, not an invalid quote. Do not interpret 21 supported positives as 21 proven fully correct answers. No independent human review or semantic judge score is claimed.

All five negatives, including q30, were refused by vector and hybrid in this run. q30's false-premise label policy still needs independent review; the earlier model's cited explanation is not retrospectively relabeled or erased. The frozen dataset is development data. A fresh held-out check and human review are still needed before generalizing these results.

## Provenance and reproduction

- Application/workflow revision: `a0e83ef53f2462e166deb2aecee98bda7ec4c17e`.
- Golden SHA-256: `b1307136fd933bf5b2cf36a1208304e1dfc06dc69f8c939a4a73b95e78224c56`.
- Index profile: `4a3e52273c1fcc3f62adc29a0d5a10b20b4b5757447d1fb87e8bf333686da91d`.
- Artifact: `12668032473`; verified ZIP SHA-256 `457278b91438bf209c3c1a5c2bd98872f8d35e6715e7f425f6e56f396fcb04e8`.
- Gemini pacing: 12 chat attempts/minute, 90 embedding inputs/minute, including retries; process-local, not daily/token or cross-process quota enforcement.
- Three provider attempts, 30/60-second retry backoff; optional question delay zero. Provider pacing within a request, retries, and failures count toward latency. API deadlines do not apply to CLI evaluation.
- `working_tree_dirty=false` for vector and `true` for later strategies because earlier generated Markdown reports were untracked. The workflow made no intervening source changes; original flags are preserved.
- [Original per-strategy JSON/Markdown and checksums](20261026_flashlite/README.md) preserve all 90 rows. Aggregates were recomputed from those rows. No LLM faithfulness judge was used.

The manual workflow at this revision skipped browser checks after the vector failure. The workflow-only follow-up `15866de4c736a5e36379f1dcd8e3e7b8d2ef9d02` fixes that guard. A separate keyword/browser validation uses the same application code; it does not replace any row in this comparison.

## Real browser validation

[Separate browser run](https://github.com/garvj65/cite-rag/actions/runs/40360595059)
**passed** on workflow revision `15866de4c736a5e36379f1dcd8e3e7b8d2ef9d02`,
with unchanged application/prompt code. It reindexed the corpus, ran keyword
operational checks, then submitted q01/q05 through Chromium against the real
FastAPI/Vite UI. Both responses had `mode=model`; q01 displayed one matched quote
and correct physical PDF page link, and q05 refused without citations. Its one
returned quote was independently source-checked. Source links were inspected,
not followed. Normal offline CI separately tests production nginx wiring.

[Browser records, exact screenshots, checksums and operational recheck](20261026_flashlite/browser-validation/README.md)
are preserved separately from the 90-row comparison. Artifact `12670031340`, ZIP
SHA-256 `23c0edcd18d71cb7bead933534ce1dadd1295463a2f279a64eb4894a915f6759`.
The README screenshot is this real q01 capture. Its final sentence also turns
“should” into “must”; passing UI and quote checks does not resolve semantic wording
faithfulness. No answer was edited for presentation. No full chat benchmark was
repeated or selectively replaced to get a cleaner comparison.
