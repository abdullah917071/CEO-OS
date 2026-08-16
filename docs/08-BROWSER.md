# Browser

Milestone 5 implements DOM-first browser execution with Playwright and managed Chromium. The CEO,
planner, and capability registry depend on the project-owned `BrowserRuntime` protocol rather than
Playwright directly, leaving room for additional browser providers without changing the kernel.

## Sessions and lifecycle

Each validated session name maps to an isolated Playwright `BrowserContext`. Incognito sessions are
the default. Optional persistent storage state is stored only beneath the configured browser data
root, with owner-only directory and file modes, and is never included in tool results or status.
FastAPI starts and shuts down the provider through its lifespan.

The direct owner endpoints are:

- `GET /api/v1/browser/status`
- `POST /api/v1/browser/stop`
- `POST /api/v1/browser/resume`

A generation-based global stop cancels the current Playwright operation, closes every context, and
blocks new work. Resume permits new commands but never replays a cancelled command.

## Navigation and extraction policy

Navigation accepts only `http` and `https`, rejects embedded credentials and fragments, and
requires an exact normalized origin match from `CEO_OS_BROWSER_ALLOWED_ORIGINS`. Request routing
applies the same rule to redirects and subresources, providing the V1 SSRF and data-egress boundary.

Extraction returns bounded visible text, title, current URL, links, and form controls. Results carry
an explicit untrusted-content marker: page content is evidence, not authority, and cannot modify the
task objective or permissions.

## Actions and artifacts

Locators are structured and strict: role/name, label, placeholder, text, test ID, or CSS. XPath,
arbitrary JavaScript, coordinates, and unsupported locator kinds are rejected. Click and fill
operations verify observable postconditions. Popup pages are tracked as tabs.

Uploads can read only from configured workspace roots. Downloads wait for Playwright's download
event, sanitize the suggested filename, and save only below the configured download root.

Safe read capabilities are registered by default. Click, fill, upload, and download are R2 effects
and exist only when `CEO_OS_BROWSER_EFFECTS_ENABLED=true`. Effect calls support process-local
idempotency keys. Screenshots, OCR, vision targeting, CAPTCHA bypass, and coordinate clicking remain
future milestones.

## Configuration

- `CEO_OS_BROWSER_ENABLED`
- `CEO_OS_BROWSER_HEADLESS`
- `CEO_OS_BROWSER_EFFECTS_ENABLED`
- `CEO_OS_BROWSER_PERSISTENT_SESSIONS`
- `CEO_OS_BROWSER_ALLOWED_ORIGINS`
- `CEO_OS_PLAYWRIGHT_BROWSERS_PATH`
- `CEO_OS_BROWSER_TIMEOUT_SECONDS`

Deterministic tests use a loopback fixture rather than external websites. They exercise navigation,
extraction, forms, popup tracking, uploads/downloads, isolation, persistence, request blocking,
policy rejection, cancellation, and capability risk boundaries with a real Chromium process.
