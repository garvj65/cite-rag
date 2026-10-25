# Configuration review, 2026-10-25

Both M3 review findings are **non-blocking with the current defaults** and do not
prevent M4 evaluation. They remain real coupling issues when settings change.

| Finding | Current behavior | Change rule |
|---|---|---|
| Query length | The UI and backend both use 2,000 characters; the backend always enforces its own limit. | Until a shared client-configuration endpoint is added, change the UI constant and backend setting together. Lowering the backend limit alone causes rejected submissions; raising it alone leaves the UI more restrictive. |
| Proxy timing | nginx uses a 240-second read timeout; normal default provider retries use a 30-second HTTP timeout and at most three attempts, with 1/2-second backoff. | Review the complete retrieval-plus-generation path whenever provider timeouts/retry counts increase, and update the proxy with it. HTTP client timeouts are not a strict end-to-end wall-clock deadline. |

M4's CLI calls application services directly, without the frontend proxy or UI
query constant. Golden validation uses the backend's configured query bound.
Keeping these defaults avoids either mismatch during this milestone. A shared
UI configuration and an end-to-end request deadline remain follow-ups before
changing the deployment settings; neither is silently claimed as fixed here.

The user also requested a more stylish, expressive, and capable UI/UX redesign
**later**. Preserve the current accessible loading/error/refusal/citation behavior
when revisiting the design. No new feature list or visual redesign is approved
as part of M4.
