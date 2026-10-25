# CiteRAG frontend

React + TypeScript + Vite research workspace: backend-owned query/retrieval
controls, distinct loading/error/refusal states, an answer panel, and an
expandable citation rail. Dark responsive styling uses system fonts and CSS
illustrations; no font/CDN requests or UI component framework are needed. Answers and
quotes render as text. Source links accept HTTP(S) only, with physical PDF page
fragments. Scripted responses have an explicit demo label.

The main README documents the four-command Docker startup at port 8080.
For frontend development, use Node 24 and start the backend at port 8000:

```bash
npm ci
npm run dev
```

Vite proxies `/api` to the backend. Production uses the unprivileged nginx image
and the same-origin proxy, so no API keys or frontend CORS configuration are needed.
Keep all provider credentials in the backend environment.

Checks: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.
`npm run test:e2e` expects the local built application at port 8080 and an installed
Playwright Chromium (`npx playwright install chromium`). Browser tests intercept
answer requests and block non-loopback requests; HTTP smoke checks separately
verify the complete Compose proxy/backend flow using explicit fake providers.


`GET /api/config` supplies query limits, default strategy/k, and maximum k.
The UI waits for a valid response before enabling submission, and offers a retry
if it fails. It counts Unicode code points to match Python, clears stale answers
when inputs change, and aborts pending fetches on unmount.

The nginx template renders `PROXY_TIMEOUT_SECONDS` from the Compose environment.
Use `docker compose up --build --wait frontend` after changing it. Backend
settings require proxy timeout ≥ API response deadline + five seconds.

CI sets `E2E_LIVE_CONFIG=1` and runs an additional browser check against the real
proxy with nondefault backend limits. Without that environment, this one check
is explicitly skipped; the other browser tests use deterministic API fixtures.
