# Operate, verify, and deploy

`.env.example` and the typed `backend/app/settings.py` are the configuration
reference. Keep real credentials in an untracked `.env` or Actions secrets.
Never paste keys in chat, commit them, or log provider bodies/document text.

## Configuration boundaries

Client query limits and response deadlines share backend-owned configuration.

| Finding | Resolution | Verification |
|---|---|---|
| Duplicated query limits | `GET /config` exposes only query/retrieval bounds and defaults. The UI loads these before enabling submission, counts Unicode code points like Python, and blocks submission if configuration cannot load. | API and component tests use nondefault limits; CI checks a deployed 173-character limit through nginx and Chromium. |
| Proxy timing | `/ask` and `/search` enforce `REQUEST_DEADLINE_SECONDS` (90 by default). nginx renders `PROXY_TIMEOUT_SECONDS` (100 by default) from the same Compose environment. Settings require at least five seconds of proxy margin. | Controlled blocked-worker tests prove a sanitized 504 reaches the caller before the worker finishes, without prematurely closing its resources. CI verifies a nondefault rendered nginx timeout. |

Provider timeouts and retry backoff are capped by the remaining API budget.
Synchronous HTTP/database work already running in a worker cannot be forcibly
terminated; it owns its cleanup and may finish after the response deadline.
The deadline bounds response waiting, not remote computation or billing.
It begins after request validation and service dependency resolution, before
queuing the search/answer operation. It is not an upload/body-read deadline.

Changing `PROXY_TIMEOUT_SECONDS` requires recreating the frontend as well as the
backend: `docker compose up --build --wait frontend`. Invalid deadline/proxy
combinations fail backend settings validation. The public configuration endpoint
never returns keys, database URLs, provider credentials, or document text.

CLI ingestion/evaluation retain their explicit provider timeout/retry settings;
they do not inherit the HTTP response deadline. The evaluation CLI can pace
questions with `--delay-seconds`, excluding that intentional waiting from latency.
These fixes do not calibrate answer thresholds or replace a real golden benchmark.

### Provider pacing and evidence gates

The explicit budget model is `gemini-3.5-flash-lite`, retaining
`gemini-embedding-2` and vector retrieval by default. Local pacing spaces every
Gemini HTTP attempt, including retries, and enforces a rolling-minute budget.
The defaults are 12 chat attempts and 90 embedding inputs/minute, conservatively
charging each input in a synchronous batch. The manual workflow uses 4 chat
attempts/minute for explicitly selected 3.6/3.8 Flash. Zero disables local pacing.
Embedding batch size must fit a nonzero input budget.

Pacing is shared by endpoint within one process, without storing keys. Separate
processes or different pacing configurations are independent; daily/token quotas,
other account users, and provider capacity remain external limits. CLI/evaluation
have no API deadline; API waiting honors the existing deadline. Pacing within a
question is part of measured latency; optional between-question pauses are not.

Hybrid results now retain vector/keyword component scores. A chunk must pass
either existing component threshold; RRF never establishes evidence strength.
High fused rank cannot promote weak scores, and a strong single-source result no
longer fails solely because its RRF score is below 0.02. Thresholds were not
calibrated on the frozen golden data. Old reports and labels remain unchanged.


## Verification

From the repository root with Python 3.12 and uv:

```bash
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=eval
uv run coverage report --include='backend/app/*' --fail-under=85
uv run python -m eval.validate
```

From `frontend/`:

```bash
npm ci --no-audit --no-fund
npm run lint
npm run typecheck
npm test
npm run build
npx playwright install --with-deps chromium
npm run test:e2e
```

Backend tests block external sockets and mock all provider HTTP. PostgreSQL
integration tests require `TEST_DATABASE_URL` pointing to a disposable local
pgvector database whose name ends in `_test`; they truncate tables and exercise
migrations. Without it, 24 database tests are explicitly skipped. CI supplies it.
The browser configuration check needs the Compose service (`E2E_LIVE_CONFIG=1`);
see [the frontend guide](../frontend/README.md). Offline CI also checks real nginx
wiring, nondefault query bounds/deadlines, Docker builds, and idempotent ingestion.
These fixtures do not measure model quality.

At merged revision `14ffcca`, [full CI](https://github.com/garvj65/cite-rag/actions/runs/40365696888)
passed 341 backend/evaluation tests (24 PostgreSQL), 99.77% app branch coverage,
38 component tests, and five browser checks. Historical evidence lives in
[the changelog](../CHANGELOG.md); new cleanup verification is recorded there once complete.
The 2026-10-26 real benchmark and browser evidence remain immutable under
`eval/results/`. Follow [the evaluation guide](../eval/README.md) for real calls.

## Private free-tier deployment

Host the existing Compose stack on a Linux VM. This runbook does not create cloud
resources or claim a live deployment. PostgreSQL 16 and pgvector remain unchanged.

### Host option

As checked on 2026-10-25, Oracle's official
[Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
lists Ampere A1 allocations equivalent to **2 OCPUs and 12 GB memory** for an
Always Free tenancy in its home region. Capacity can be unavailable and idle
instances can be reclaimed. Select resources labeled Always Free and check the
account's current limits; no paid upgrade or availability guarantee is implied.

Use eligible Ubuntu 24.04 and install Docker Engine/Compose using
[Docker's instructions](https://docs.docker.com/engine/install/ubuntu/).
CI validates Linux x86-64 containers; the ARM deployment path has not been tested
here. Check image pulls/builds on that host. A small-memory micro VM can run out
of memory during frontend compilation; A1 has more suitable headroom.

### Private portfolio demo

SSH into the VM and follow the main README's four-command startup. Replace the
example database password **before first start**, using a URL-safe random value.
Changing `.env` later does not change an initialized database password.

Keep loopback bindings. From your own computer, forward the UI:

```bash
ssh -N -L 8080:127.0.0.1:8080 ubuntu@YOUR_VM_HOST
```

Open `http://localhost:8080` in your browser; no local build or GPU is needed.
Only SSH needs remote access. Keep database/API/UI ports off the public network.
Download/ingest and evaluate on the VM using the README commands.

| Environment | Settings |
|---|---|
| Database | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`; Compose supplies internal `DATABASE_URL` |
| Real Gemini | `EMBEDDING_PROVIDER=gemini`, `LLM_PROVIDER=gemini`, `ENABLE_REAL_PROVIDERS=true`, `GEMINI_API_KEY` |
| Mechanics demo | `EMBEDDING_PROVIDER=fake`, `LLM_PROVIDER=fake`, `ENABLE_REAL_PROVIDERS=false` |
| Optional OpenAI | Explicitly select providers and configure `OPENAI_API_KEY` and `OPENAI_CHAT_MODEL`; no automatic fallback |
| Reproduction | Matching model/chunk settings, golden data, dependency locks, code revision |

All settings are in `.env.example`. Keep credentials in the VM's untracked `.env`,
readable by its owner. Account billing/quota determines whether provider usage is
free; the app cannot enforce the account tier. Scripted defaults refuse and do
not simulate model reasoning.

### Operate and update

Check `docker compose ps` and `docker compose logs --tail 100 backend`. After an
update or VM reboot run `docker compose up --build --wait frontend`; migrations
run before the API. Named-volume persistence is not a backup.

Back up before migrations/host changes to the gitignored directory:

```bash
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backups/citerag.sql
```

Keep an external copy and test restoration into a separate empty database.
`docker compose down --volumes` deletes the volume; do not use it on useful data.
Keep original PDFs, settings, code, golden data, and external backups for recovery
if a free-tier host is reclaimed.

### Public hosting boundary

The app has no authentication or application rate limiting. This runbook is a
private demo through SSH. Public hosting with real provider credentials needs an
explicit access/quota policy and HTTPS termination. No public production service
has been deployed. The configuration section above documents shared client limits and response deadlines. Recreate both frontend and backend after changing
`PROXY_TIMEOUT_SECONDS`; settings require at least five seconds beyond
`REQUEST_DEADLINE_SECONDS`. The deadline limits response waiting, not already
in-flight remote work. A public deployment is outside this private-demo runbook.
