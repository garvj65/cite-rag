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
The committed dataset contains 25 answerable and five unanswerable questions:
[questions, answer key, and source evidence](../eval/golden-review.md). It was
assistant-authored, source-checked, reviewed by the user on 2026-10-27, and
[measured with real providers](../eval/results/README.md). It is development data.

When encoding `eval/golden.jsonl`, use the full document hash above. See
[the evaluation guide](../eval/README.md) for schema, validation, and real runs.
If NIST replaces a PDF its identity can change even at the same URL. Verify the
version before labeling. The manual workflow verifies downloaded identities and
indexed gold pages before evaluation.
