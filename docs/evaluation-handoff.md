# Run the real benchmark from your browser

The app, automated checks, and evaluation machinery are implemented. The real
quality benchmark still needs **your own golden questions/pages** and access to
the chosen Gemini models. The project cannot honestly substitute a fake-provider
run for those measurements. M5 remains outside this release until M4 is measured.

1. Read the two PDFs in the [corpus reference](corpus-reference.md). Write your
   questions and labels in `eval/golden.jsonl` using [the schema](../eval/README.md).
   GitHub's editor is sufficient; no local build is needed. You may instead send
   your questions, short document names, and physical pages in chat for formatting.
2. In the repository, open **Settings → Secrets and variables → Actions → New
   repository secret** and add **`GEMINI_API_KEY`**. Keep the value in GitHub's
   secret form, never source code, an issue, or chat. Use your intended account
   tier and review its quota/billing settings; no paid fallback exists.
3. After this workflow is on the default branch, open **Actions → Explicit Gemini
   evaluation → Run workflow**. Select the branch containing your dataset, choose
   `hybrid` initially, and explicitly enable **Allow Gemini API calls**. Leaving
   the checkbox off skips the job. `all` runs vector, keyword, and hybrid in order
   and consumes more quota. The default 15-second pause helps pace chat calls but
   does not guarantee your account's quotas, especially during embedding batches.
4. Download the **measured-evaluation** artifact and review the run summary table,
   class counts, errors, citation counts, answers, and reproduction metadata. Files
   are retained for 14 days. Save reviewed results before expiry. A failed run may
   still contain useful partial results, clearly marked with errors.
5. Commit reviewed Markdown results under `eval/results/` and replace the README's
   pending cells with those exact measurements and the run link. Raw JSON/JSONL
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
