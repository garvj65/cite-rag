# Run the real benchmark from your browser

The app, automated checks, and evaluation machinery are implemented.
[The first real runs](../eval/results/20261026_gemini_baseline.md) are preserved,
including rate-limit failures and refusal gaps. A reliable answer benchmark still
needs **independently reviewed golden labels** and sufficient model quota. A 30-question assistant-authored baseline is encoded at your request;
it is ready for your review, not an independent benchmark. The project cannot honestly substitute a fake-provider
run for those measurements. M5 remains outside this release; resolve the measured reliability/refusal gaps first.

1. Review [the 30 questions, answer key, and source checks](../eval/golden-review.md)
   against the two PDFs in the [corpus reference](corpus-reference.md). The encoded
   file is `eval/golden.jsonl`; independent human review is pending. Use the branch
   containing the baseline for the first run. The original q01–q05 remain intact;
   q01–q30 now provide 25 answerable and 5 unanswerable questions. GitHub's editor is sufficient; no local build is needed.
2. In the repository, open **Settings → Secrets and variables → Actions → New
   repository secret** and add **`GEMINI_API_KEY`**. Keep the value in GitHub's
   secret form, never source code, an issue, or chat. Use your intended account
   tier and review its quota/billing settings; no paid fallback exists.
3. Open **Actions → Explicit Gemini
   evaluation → Run workflow**. Select the branch containing your dataset, choose
   `vector` initially, and explicitly enable **Allow Gemini API calls**. Leaving
   the checkbox off skips the job. `all` runs vector, keyword, and hybrid in order
   and consumes more quota. The default 15-second pause helps pace chat calls but
   does not guarantee your account's quotas, especially during embedding batches.
4. Download the **measured-evaluation** artifact and review the run summary table,
   class counts, errors, citation counts, answers, and reproduction metadata. Files
   are retained for 14 days. Save reviewed results before expiry. A failed run may
   still contain useful partial results, clearly marked with errors.
5. Commit reviewed Markdown results under `eval/results/` and replace the README's
   measured cells only with the new exact measurements and run link. Raw JSON/JSONL
   are gitignored because they contain questions, generated answers, and quotes.

The workflow uses a disposable PostgreSQL 16/pgvector database, downloads only
the approved manifest corpus, migrates, ingests, verifies gold pages, and calls
the existing evaluator. It does not deploy the app or modify Git. Only a manual
workflow dispatch enables real API calls; normal CI never calls model providers.
The key is not needed for schema validation or deterministic tests.

If the workflow stops on quota, model access, or provider errors, inspect the
sanitized error counts and account configuration. It never switches providers.
Question pacing is configurable from 0 to 300 seconds and is excluded from
per-question latency. The seed fixes order, not model output or network timing.

Citation validity means the quotes occur in supplied chunks. It does not measure
semantic entailment of every answer claim. No LLM faithfulness judge is used.
Human review and real adversarial testing remain necessary before describing
answer faithfulness or injection resistance as established.


## Provider access preflight

The workflow now runs `scripts/check_providers.py --allow-real-calls` before
corpus ingestion. It makes a tiny embedding request and a schema-constrained
chat request through the actual adapters. It prints component outcomes, numeric
HTTP statuses, and allowlisted provider error/reason codes only. It never prints
API keys, authorization headers, prompts, generated text, vectors, or provider
error messages/bodies. Local tests use MockTransport and require no secret.

A preflight failure stops the expensive ingestion/evaluation path. HTTP 400 with
API_KEY_INVALID indicates credential trouble; 401/403 indicate authentication or
access issues; 404 can indicate unavailable models/endpoints; 429 indicates quota
or rate limits. Inspect the safe codes and the provider account configuration.
No provider or model is silently replaced. Account-specific failures need the
account owner to fix access or replace the repository secret securely.

The manual workflow also exposes an explicit `chat_model` choice. The app default
remains Gemini 3.8 Flash. Selecting Gemini 3.6 Flash is a separate configured
experiment, recorded in its metadata; it is never an automatic fallback. Google
[lists free tiers](https://ai.google.dev/gemini-api/docs/pricing) for both, subject
to account quotas and eligibility. Do not combine results from different chat
models without labeling them.

For ranking measurements during chat outages or quota exhaustion, explicitly
check **Measure retrieval only**. This skips chat preflight and generation,
leaving citation/refusal/answer metrics N/A. It measures retrieval latency only;
do not compare it with full answer latency. You can reduce question pacing for
this mode subject to embedding quotas. The mode is recorded in each JSON report
and displayed in the aggregate table. Full answer evaluation remains a separate
run with this checkbox off.
