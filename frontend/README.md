# CiteRAG frontend

React + TypeScript + Vite interface for `/ask`: a question form, loading/error
states, evidence refusals, and expandable verified citation cards. Answers and
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
