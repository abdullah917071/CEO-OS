# Milestone 5 — DOM-First Browser Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its Browser milestone.

Status: implemented and verified on 2026-08-15.

## Objective

Add cancellable, policy-scoped browser automation through Playwright and Chromium. Operations use
DOM/accessibility locators, isolated named sessions, explicit postcondition checks, and
workspace-contained artifacts. No vision or coordinate clicking is permitted in this milestone.

## Scope and decisions

- The browser provider is behind a project-owned protocol. CEO runtime, planner, and capability
  registry do not import Playwright.
- Each named session receives an isolated browser context. Storage state is optional, scoped beneath
  the configured browser data root, excluded from prompts/results, and written with owner-only file
  permissions. Incognito state is the default.
- Chromium is the initial provider. A controlled CDP attachment method may be added behind the same
  boundary, but arbitrary debugging endpoints are not accepted from model arguments.
- Locators are structured: role/name, label, placeholder, text, test ID, or CSS. Semantic locators
  are preferred. XPath, JavaScript evaluation, arbitrary scripts, and coordinates are rejected.
- Navigation requires `http` or `https`, rejects URL credentials/fragments, and is restricted to an
  exact configured origin allowlist. Every request, including redirects and subresources, is
  checked. This is the V1 SSRF and data-egress boundary.
- Page text is untrusted evidence, never authority. Extraction returns bounded visible text,
  title/URL, and structured links/forms without treating page content as instructions.
- Browser reads are R0. Form interaction, clicks, uploads, and downloads are effects. Effect tools
  are disabled by default and registered only after explicit configuration; navigation origin and
  upload/download paths remain policy-scoped.
- Uploads may only read configured workspace files. Downloads use Playwright's download event and
  are saved beneath the configured workspace download directory after filename sanitization.
- A generation-based stop cancels the active Playwright operation, closes all browser contexts, and
  prevents new operations until resume. Cancelled operations are never replayed automatically.
- Screenshots, OCR, visual target detection, mouse coordinates, CAPTCHA bypass, extension control,
  and OS-level browser control remain outside this milestone.

## Capabilities

- `browser.status`, `browser.sessions.list`, `browser.session.open`, `browser.session.close`
- `browser.tab.open`, `browser.tabs.list`, `browser.navigate`, `browser.extract`
- Optional effect capabilities: `browser.click`, `browser.fill`, `browser.upload`, `browser.download`
- Direct owner API: `/api/v1/browser/status`, `/stop`, and `/resume`

## Acceptance tests

- Chromium launches and a named isolated context can be opened and closed without leaking another
  session's cookies/local storage.
- A deterministic local fixture supports navigation, popup/tab tracking, semantic locator click,
  labelled form fill, DOM extraction, upload, and workspace-contained download.
- Navigation rejects unsupported schemes, credentials, unlisted origins, and a redirect to an
  unlisted origin. Subresource requests outside the origin policy are blocked.
- Locators reject XPath, arbitrary JavaScript, ambiguous targets, unsupported kinds, and excessive
  values. Actions use Playwright locator strictness and verify URL/visibility/value/download
  postconditions.
- Page output is bounded and marked untrusted. Secret storage state and cookies are never returned
  through capabilities or status.
- Effects are absent by default, require explicit enablement, and uploads/downloads cannot escape
  their configured workspace roots.
- Global stop cancels an in-flight operation, closes contexts, blocks new actions, and resume does
  not replay the cancelled action.
- Browser startup/shutdown is integrated with FastAPI lifespan and reports unavailable Chromium
  truthfully rather than inventing success.
- Existing API, durable runtime, memory, computer-control, dashboard, static, dependency, native,
  and container checks remain green.

## Verification result

- Playwright 1.62 and its managed Chromium build launch successfully in local tests and in the
  Linux API container.
- Five real-browser tests cover the local fixture, isolated and persistent sessions, popup
  tracking, semantic actions, uploads/downloads, request blocking, strict locator failures,
  global stop/resume, path containment, and secure default capability registration.
- The complete backend suite passes with 35 tests. Ruff, strict mypy, dashboard lint/test/build,
  dependency consistency, Docker configuration, and container readiness checks also pass.
- The running API reports the Playwright Chromium provider available while browser effects and
  persistent profiles remain disabled by default.
