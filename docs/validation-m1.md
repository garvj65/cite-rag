# M1 validation record

Verified on 2026-10-24 against implementation commit
`e368f47d668359ede396a340d5c774ed9c9f400a`.

## Automated checks

[GitHub Actions run](https://github.com/garvj65/cite-rag/actions/runs/40087791508)
completed successfully:

| Check | Result |
|---|---|
| Ruff lint and formatting | Passed |
| Strict mypy on application and scripts | Passed |
| Pytest against PostgreSQL 16/pgvector | 83 passed, 0 skipped |
| Backend application coverage, including branches | 99.62% |
| Backend Docker image build | Passed |
| Compose configuration validation | Passed |

Integration tests include concurrent identical ingestion, profile isolation,
pgvector round-trip dimensions, source metadata, rollback of all document writes
when a chunk violates a constraint, and migration downgrade/upgrade. The invalid
chunk test intentionally causes a database constraint error; its rollback is
asserted, rather than treating the error as successful ingestion.

Local checks used Python 3.12.14: 78 passed and 5 explicitly skipped because
`TEST_DATABASE_URL` was absent, with 96.35% application coverage. PostgreSQL checks
were then completed in CI. Test HTTP uses deterministic mock transports, and
external Python sockets are blocked. No authenticated provider calls were made.

## Public corpus extraction smoke check

The manifest downloader fetched the actual PDFs. `extract_pages` followed by
`chunk_pages(size=400, overlap=80)` produced:

| Document | Bytes | PDF pages | Empty pages | Chunks |
|---|---:|---:|---:|---:|
| NIST AI RMF 1.0 | 1,946,127 | 48 | 0 | 66 |
| NIST Generative AI Profile | 1,174,643 | 64 | 0 | 83 |
| Total | 3,120,770 | 112 | 0 | 149 |

PDF SHA-256 identities:

- AI RMF: `7576edb531d9848825814ee88e28b1795d3a84b435b4b797d3670eafdc4a89f1`
- Generative AI Profile: `6e73620ab6b64e90ef2c04bf0e0d6246185a2f4b1b13cab0df494496cff89b6a`

The PDFs are gitignored. This smoke check validates extraction and chunking;
it does not measure semantic retrieval, answer faithfulness, or live-provider
compatibility. Those require the later milestones and user-authored golden data.

## Review boundaries

Review physical page numbering, exact chunk offsets, duplicate/profile behavior,
the proposed two-document corpus, and explicit provider/budget configuration.
M2 retrieval, M3 answers/UI, and M4 evaluation have not been implemented.
