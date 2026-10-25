# Starter corpus reference

These are the two approved public AI risk-management PDFs, downloaded and checked
on 2026-10-25. PDFs stay out of Git. Use the **physical page shown by your PDF
viewer**, including the cover and contents, rather than the printed page label.

| Short name | Document | Physical pages |
|---|---|---:|
| RMF | [NIST AI Risk Management Framework 1.0](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf) | 48 |
| GenAI | [NIST Generative AI Risk Management Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | 64 |

Document identities (SHA-256 of the downloaded original bytes):

```text
RMF:   7576edb531d9848825814ee88e28b1795d3a84b435b4b797d3670eafdc4a89f1
GenAI: 6e73620ab6b64e90ef2c04bf0e0d6246185a2f4b1b13cab0df494496cff89b6a
```

To author golden data without running the project, read these PDFs in a browser
and provide your own questions, whether each is answerable, and the short name
plus physical page(s) supporting it. A human reference answer is optional; it is
not automatically scored. Deliberately unanswerable questions have no gold pages.
The planned dataset is 25 answerable and 5 unanswerable questions; you can start
with fewer. No questions or reference answers have been supplied by the app.

When translating your labels into `eval/golden.jsonl`, replace the short name with
its full hash above in each `gold_pages` entry. The schema and validator are in
[the evaluation guide](../eval/README.md). You can also send your own questions
and labels in chat for formatting into JSONL; do not include credentials.

If NIST replaces a PDF, its identity can change even at the same URL. Verify the
downloaded version before labeling it. The manual workflow checks document
identities before embedding and checks indexed gold pages before evaluation.
