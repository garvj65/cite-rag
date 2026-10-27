# Focused wording check — 2026-10-27

This is a development regression check on eight existing questions, not a new
30-question benchmark or held-out accuracy estimate. It does not replace any
published comparison. Both prompt attempts are preserved, including the first
attempt's failure to correct q01 and the second attempt's additional refusals.

The user confirmed reviewing the answer key on 2026-10-27 and deliberately kept
q30 as an ambiguous false-premise edge case with its expected-refusal label. The
golden bytes remain unchanged. Six answerable questions (q01/q02/q08/q13/q20/q25)
and two negatives (q05/q30) cover source obligation, possible effects, context,
provider-timeout regression, and refusal behavior. These are known development
examples; the prompt correction is not independently validated on unseen data.

| Attempt | Strategy | Supported positives | Correct negative refusals | Errors / 8 | Raw valid/proposed quotes |
|---|---|---:|---:|---:|---:|
| 1 | vector | 5/6 | 2/2 | 0 | 7/8 |
| 1 | keyword | 0/6 | 2/2 | 0 | N/A (0 proposals) |
| 1 | hybrid | 6/6 | 1/2 | 0 | 13/13 |
| 2 | vector | 4/6 | 2/2 | 0 | 6/8 |
| 2 | keyword | 0/6 | 2/2 | 0 | N/A (0 proposals) |
| 2 | hybrid | 4/6 | 2/2 | 0 | 7/8 |

Supported counts are application outcomes, not semantic-correctness scores. Raw
citation counts include valid partners withheld when any citation failed. All
**30 released benchmark quotes across both attempts** were rechecked against
production-extracted, 400/80-word source chunks, matching document/page/chunk
index and retrieved chunk ID. The first attempt's separate browser quote was
also source-checked. Aggregate metrics were recomputed from the original rows.

## Source wording review

The source on RMF physical PDF page 19 says accuracy measurements **should** be
paired with realistic test sets and test-methodology details, which **should**
be documented. Its next sentence says measurements **may** include disaggregation.

- Attempt 1 added a general preservation rule. Both vector and hybrid still
  changed “should” to “must”; the separate real-browser q01 response did too.
  This failed the targeted semantic review despite valid quotes and successful
  software checks. Nineteen returned benchmark quotes were source-valid.
- Attempt 2 requires source clauses expressing obligation, permission,
  uncertainty, or possible effects to be copied rather than freely paraphrased,
  with a generic recommendation/mandate example and a final wording check.
  Vector q01 kept “should” for pairing and documentation; hybrid kept both
  “should” clauses and “may” for disaggregation. Hybrid q08 also retained
  context-specific risk tolerance and “can be influenced” qualifications.
  Eleven returned benchmark quotes were source-valid.

This is an assistant review of the observed outputs, not a general faithfulness
metric. The model still paraphrased parts of clauses despite the stricter
instruction, so exact clause copying is not an enforced API guarantee. No semantic
validator or LLM judge was introduced. Quote verification is unchanged and proves
provenance only. In attempt 2, vector refused q08/q25 for invalid citations;
hybrid refused q25 for invalid citations and q20 as unsupported. Vector q20
provided a mitigation recommendation rather than fully describing the possible
model-collapse effect. Completeness and answer quality remain limited.

In attempt 1, hybrid q30 gave a cited explanation that the framework is voluntary
and non-prescriptive, with no invented dollar amount. It is counted as a label
disagreement, not a correct refusal. Attempt 2 refused both negatives in both
vector and hybrid. The user's edge-case label is unchanged; a single response
does not establish stable refusal behavior. Keyword refused all positives in
both attempts and is not useful answering evidence here.

## Reproduction and records

| Field | Attempt 1 | Attempt 2 |
|---|---|---|
| Revision | `1aca66b766e3e06b06c709c0c6fcf7b9a9a04740` | `177943ee9f407ff21116b836a033c0f6b4a32c79` |
| Run | [40451211739](https://github.com/garvj65/cite-rag/actions/runs/40451211739) | [40452168497](https://github.com/garvj65/cite-rag/actions/runs/40452168497) |
| Artifact ID | 12710418292 | 12711120826 |
| ZIP SHA-256 | `bfd74332b87e54e066bae0849fc60508bcc11756d4731756daa9ed60a58ca712` | `cd93729e462269ed2e2251a26c0ffa80c5f5856b8e17404fc4ec9e723a3b370e` |
| System prompt SHA-256 | `191388ce0753a2cc804dfb327ffba71fdeb76a89d361b75c5c0fa49f970d0efc` | `ffc7155da6a849fa265d697f4cb084cb598794b5d3de7c27f4bf93adc0d0b4fe` |

Both runs completed all three strategies with zero question errors and no model
fallback. A 429 was logged and recovered through bounded retry in attempt 1;
attempt 2 logged no HTTP provider failures. Each uses Gemini 3.5 Flash-Lite,
Gemini Embedding 2, k=5, seed=42, 400/80-word chunks, 12 chat attempts/minute,
90 embedding inputs/minute, and zero between-question delay. In-request pacing
and retries count toward latency. Both revisions use the same provisional
0.35 cosine / 0.05 FTS gates; neither thresholds nor labels changed.

Golden SHA-256: `b1307136fd933bf5b2cf36a1208304e1dfc06dc69f8c939a4a73b95e78224c56`.
Each original JSON records the full golden digest, selected IDs, prompt digest,
models, index profile, safe settings, raw answers/refusals/errors, and latency.
[Original JSON and checksums](20261027_wording/SHA256SUMS) retain all 48 benchmark
attempts without redundant Markdown/JSONL copies. Browser response JSON from
attempt 1 is included; its original screenshots remain in the linked Actions
artifact for its retention period. The older permanent UI captures stay unchanged.

## Index reuse verification

The initial cache key included generated Python bytecode; a second job missed
that cache and unnecessarily reingested the corpus. Revision `177943e` restricts
fingerprints to source files and PDF bytes. Attempt 2 built the corrected cache
once. A subsequent [retrieval-only operational check](https://github.com/garvj65/cite-rag/actions/runs/40452444820)
restored the exact compatible snapshot, passed gold/index validation, completed
eight keyword queries with zero errors, and skipped ingestion plus all Node/
Chromium setup/checks. Its preflight made one tiny embedding request and no chat
calls. It is an operational check, not an additional answer-quality measurement.
The original failed reuse check is retained in [run 40451700608](https://github.com/garvj65/cite-rag/actions/runs/40451700608).

Corrected cache key:
`public-index-pg16-pgv081-v1-Linux-0383ac30c30f5c5553110c92f040f71a66985afb31636e2cdc49d39ad210e984`.
The snapshot contains only the approved public corpus/index. It is not committed.
All strategies and optional browser checks share the one restored/built DB within
a job. Browser checks default off; downloaded Chromium binaries are cached.
Fresh runner OS libraries still need installation when browser checks are enabled.
Eviction, branch visibility, or changed index inputs can legitimately require a
rebuild. No arbitrary-prefix cache fallback or distributed service was added.
