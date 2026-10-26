# Golden pilot review

Version: 2026-10-26. Five assistant-authored entries prepared at the user's explicit request:
four answerable and one unanswerable. Labels/reference answers were checked against the fixed
public PDFs, independently of any CiteRAG answer. Independent human review and a real-provider
evaluation are still pending.

This pilot checks the evaluation path. It is not the planned 25-answerable/5-unanswerable
benchmark, a representative sample, or proof of model quality. One negative cannot establish
reliable refusal accuracy. Reference answers are review aids; the current harness does not
automatically score semantic agreement or faithfulness.

## Questions and answer key

| ID | Question | Reference answer / expected behavior | Gold page |
|---|---|---|---|
| q01 | What should accompany an AI system's accuracy measurements, according to the AI Risk Management Framework? | Clearly defined, realistic test sets representative of expected use, plus details of the test methodology in the documentation. | [RMF, physical page 19](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=19) |
| q02 | At what stage should AI safety considerations begin, according to the AI Risk Management Framework? | As early as possible, during planning and design, with safety considered throughout the lifecycle. | [RMF, physical page 20](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf#page=20) |
| q03 | Besides false content, what two kinds of inconsistency does the Generative AI Profile include under confabulation? | Outputs that diverge from the prompt or input, and outputs that contradict earlier statements in the same context. | [GenAI, physical page 10](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=10) |
| q04 | Which two model-size reduction methods does the Generative AI Profile mention for reducing environmental impacts during inference? | Model distillation and compression; training and tuning these smaller models may still contribute environmental impacts. | [GenAI, physical page 12](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf#page=12) |
| q05 | How many confirmed AI safety incidents worldwide in calendar year 2025 are reported in these documents? | Refuse: the documents do not report this count. No reference_answer or gold pages are encoded. | None |

## Source checks

Physical page numbers include covers and contents. RMF physical pages 19/20 have printed labels
14/15; GenAI physical pages 10/12 have printed labels 6/8. Document identities are SHA-256
hashes of the original PDF bytes; see [the corpus reference](../docs/corpus-reference.md).

Short evidence anchors below are working notes, not extra fields in the strict golden JSONL.
Each anchor appears on its labeled page and all anchors for each entry fit within one default
400-word chunk (80-word overlap), checked using the production extractor/chunker. The
surrounding source text supports the reference answer.

- q01: “and details about test methodology”.
- q02: “starting as early as possible with planning and design”.
- q03: “diverge from the prompts or other input”; “contradict previously generated statements in the same context”.
- q04: “model distillation or compression”.

q05 absence check: searched all 112 extracted physical pages; neither PDF contains the year
2025. Publication dates are January 2023 (RMF) and July 2024 (GenAI), so neither reports a
confirmed full-calendar-year 2025 global incident total. The question requests that missing
count; a guessed number or substituted statistic from another year is unsupported.

Gold pages are canonical evidence labels, not an exhaustive list of every possibly equivalent
passage. Review an apparent retrieval miss before concluding that no valid evidence was found.
Do not add a second gold page merely as an interchangeable alternative: this harness treats
multiple gold pages as jointly expected for recall.

## Validation and next step

Golden SHA-256: `31bd35e6e31ced96902a4408231e33c88630883ef5f0bb8021609a7cb173e385`.

`uv run python -m eval.validate` checks field types, IDs, labels, and query bounds without an
API key or database. Local source/hash/page/chunk checks described above also passed. Index
preflight (`--check-index`) and real provider measurements remain pending.

Review these five entries before the pilot run. Use the [browser evaluation
handoff](../docs/evaluation-handoff.md) with strategy hybrid, k=5 (workflow default), and the
repository secret. A real run uses the branch containing this file. Preserve the dataset digest
and code revision with any results.

Expand the dataset across both PDFs after the pilot works, including harder and multi-page
questions plus more negatives. Keep author provenance explicit, add independently
reviewed/held-out questions, and correct labels only when source evidence warrants it; changing
labels to improve a score would undermine the benchmark.
