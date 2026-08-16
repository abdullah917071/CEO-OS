# Milestone 6 — Cua Driver Vision Fallback Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its vision-fallback milestone.

Status: implemented and verified on 2026-08-15.

## Objective

Add a cancellable, evidence-bearing Cua Driver fallback for interfaces that cannot be addressed
through DOM or Accessibility semantics. CEO OS owns policy and orchestration; Cua Driver supplies
the typed capture and action runtime.

## Scope and decisions

- Vision remains the last automation tier after direct functions, shell, DOM/CDP, and native
  Accessibility operations.
- The kernel and capability registry depend on a project-owned driver protocol. Only the adapter
  imports `cua_driver`.
- The Python SDK runs in-process and is owned for the API lifespan. Runtime availability, execution
  mode, metadata, permissions, and errors are reported truthfully.
- Capture is window-scoped by default. Desktop capture and existing signed-in browser profile access
  are not enabled in V1.
- Driver image data stays inside the vision/model loop. Capability results expose bounded metadata,
  hashes, and verification evidence rather than raw screenshots.
- Mutating driver actions are R2 effects and disabled by default. Every action binds an exact PID,
  window ID, coordinate/key/text constraints, session, and task-level idempotency key.
- Cua Driver's `verified` result is preserved, and consequential completion requires an independent
  postcondition rather than trusting an action response alone.
- Stop invalidates active capture/action work and no cancelled operation is replayed on resume.
- CAPTCHA solving, stealth automation, unrestricted desktop control, arbitrary generic tool calls,
  browser-profile attachment, and automatic retries after unknown completion remain prohibited.

## Capabilities

- `vision.status`
- `vision.windows.list`
- `vision.window.capture`
- Optional bounded effect capabilities for click, type, key, and scroll
- Direct owner API: `/api/v1/vision/status`, `/stop`, and `/resume`

## Acceptance tests

- The Cua Driver SDK adapter starts and shuts down with the API and exposes content-free status.
- A deterministic fake driver validates capture metadata, exact window binding, action translation,
  verification propagation, failure handling, and unknown-completion behavior.
- Image bytes never appear in capability output, status, logs, or evidence.
- Visual effects are absent by default and require explicit configuration plus a target allowlist.
- Global stop cancels an in-flight provider operation, blocks new work, and resume does not replay.
- Status truthfully reports provider availability and policy without returning image content.
- A live macOS smoke test captures and changes a fixture through Cua Driver when Screen Recording and
  Accessibility grants are available; otherwise it is recorded as an explicit owner-environment
  prerequisite and the milestone is not marked fully live-verified.
- Existing API, durable runtime, memory, computer, browser, dashboard, dependency, and container
  checks remain green.

## Verification result

- Cua Driver 0.19.3 reported its embedded runtime available with contract 0.6.0.
- The owner granted the responsible Cua Driver identity Screen Recording and Accessibility access;
  direct capture permission verification passed.
- A live isolated `Google Chrome for Testing` window rendered a canvas-only control. CEO OS captured
  that exact PID/window with a non-degraded PNG, translated the captured-image coordinate into the
  driver frame, delivered an explicitly authorized foreground click, and independently verified the
  exact title transition from `CEO OS CUA Fixture Ready` to `CEO OS CUA Fixture Success`.
- The live public capture result contained only MIME type, byte count, SHA-256 digest, snapshot
  metadata, and the untrusted-content marker—not screenshot bytes.
