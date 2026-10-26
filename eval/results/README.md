# Evaluation results

[The Flash-Lite quality pass](20261026_flashlite.md) measures all three strategies
on the same frozen 30-question development baseline. Hybrid returned 21/25
supported positives, refused all five negatives, and had zero errors. Vector
retained one timeout. All 45 returned quotes were source-checked; a valid quote
does not guarantee faithful wording (see the q01 review flag).
[Original JSON/Markdown and checksums](20261026_flashlite/README.md) preserve all
90 first-run records. A separate browser validation is reported alongside them;
it does not replace any comparison row.

[The 2026-10-26 measured Gemini baseline](20261026_gemini_baseline.md) reports all
three strategies on 30 assistant-authored questions (25 answerable, 5 negative).
The retrieval-only run completed without errors. The separate end-to-end attempt
retains provider failures, conservative refusals, and an expected-refusal label
disagreement; it is not a clean answer-quality benchmark.

[Original raw JSON/Markdown reports and checksums](20261026/README.md) preserve
all 180 question records beyond the Actions artifact retention window.
[Provider attempts](20261026_provider-attempts.md) record preceding failures.
Independent label review, held-out validation, and a reliable answer run remain
open. No fake-provider result is presented as semantic-quality evidence.
