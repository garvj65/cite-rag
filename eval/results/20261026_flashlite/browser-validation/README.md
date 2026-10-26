# Separate live browser validation

Run: https://github.com/garvj65/cite-rag/actions/runs/40360595059
Revision: `15866de4c736a5e36379f1dcd8e3e7b8d2ef9d02` (workflow conditions only;
application code and prompt unchanged from the comparison revision).

Artifact: 12670031340. Verified ZIP SHA-256:
`23c0edcd18d71cb7bead933534ce1dadd1295463a2f279a64eb4894a915f6759`.

The workflow completed successfully. It reindexed the approved PDFs, ran the
30-question keyword evaluation without errors, then submitted q01 and q05 through
Chromium to the real FastAPI/Vite UI. No answer responses were intercepted.
Both browser responses have `mode=model`: q01 supported with one source-matched
quote and q05 refused with no citations. The check expanded the citation and
verified its displayed quote and physical PDF page link. Its quote was separately
rechecked against the production PDF extractor/chunker.

The JSON records and screenshots are original artifact bytes. `answers-keyword.*`
were renamed from `20261026T164552353737Z_configured_keyword_k5.*` and remain a
separate operational recheck; they do not replace rows or aggregate with the
first-run three-strategy comparison. The README screenshot uses this real q01
capture, without editing generated answer text.

The q01 browser answer also strengthens source “should” to “must” in its final
sentence. A passed browser flow proves wiring/rendering and quote provenance,
not semantic faithfulness. This flag and the comparison's q01 wording flag remain
visible for human review. No independent human or judge correctness score is
claimed. Normal CI separately verifies nginx/Compose with offline fixtures.
