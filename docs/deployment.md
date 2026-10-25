# Free-tier deployment runbook

Host the existing Compose stack on a Linux VM. This runbook does not create cloud
resources or claim a live deployment. PostgreSQL 16 and pgvector remain unchanged.

## Host option

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

## Private portfolio demo

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

## Operate and update

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

## Public hosting boundary

The app has no authentication or application rate limiting. This runbook is a
private demo through SSH. Public hosting with real provider credentials needs an
explicit access/quota policy and HTTPS termination. No public production service
has been deployed. The [configuration review](configuration-review.md) documents shared client limits
and response deadlines. Recreate both frontend and backend after changing
`PROXY_TIMEOUT_SECONDS`; settings require at least five seconds beyond
`REQUEST_DEADLINE_SECONDS`. The deadline limits response waiting, not already
in-flight remote work. A public deployment is outside this private-demo runbook.
