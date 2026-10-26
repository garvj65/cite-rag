# Frozen public benchmark records, 2026-10-26

These six JSON reports and their original Markdown reports preserve the actual
configured-provider outputs. They contain assistant-authored questions, public
NIST quotes, generated answers, ranking evidence, sanitized errors, and safe
experiment metadata. They were reviewed before committing; they contain no
credentials or full source PDFs. Future user-corpus raw outputs remain gitignored.
This dated subdirectory is excluded from the workflow's root-level result glob,
so these records cannot be mixed into a future run's aggregate table.

See [the measured analysis](../20261026_gemini_baseline.md) and [SHA256SUMS](SHA256SUMS).

- End-to-end source: [run 40271174202](https://github.com/garvj65/cite-rag/actions/runs/40271174202), artifact 12629654891, ZIP SHA-256 `d0662a1b8cca00aed6d49ab3a41451d05f2a0489f0319c151cf056a2cb91be68`.
- Retrieval-only source: [run 40272916763](https://github.com/garvj65/cite-rag/actions/runs/40272916763), artifact 12630945343, ZIP SHA-256 `18555d6474379d16a65d1310ff328a6063dcdf01dcd45f514846b04323c97f36`.

The downloaded ZIP hashes matched GitHub's artifact digests. All six aggregates
were recomputed from their question records using the metric functions. All 17
returned citations in the end-to-end records were independently matched to the
production extractor/chunker's document, physical page, chunk index, and quote;
each chunk ID also appears in that question's retrieved records. The model's
one rejected proposal is represented by the verification counts, not returned
as a fabricated citation.

`working_tree_dirty` is false on the first strategy and true on later strategies:
the earlier generated Markdown reports are untracked files in the same checkout.
The workflow does not edit source/golden data between strategies. These flags
are preserved verbatim, together with the immutable source revisions. The fixed
seed controls question order, not provider behavior or network timing.
