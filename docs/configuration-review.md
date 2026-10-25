# Configuration review, resolved in release readiness

The two M3 coupling findings are addressed in this release.

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
