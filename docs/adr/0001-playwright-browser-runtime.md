# ADR 0001 — Playwright for DOM-First Browser Automation

Status: accepted on 2026-08-15.

## Context

Milestone 5 requires isolated browser sessions, stable DOM locators, navigation and action waits,
popup/tab tracking, downloads, uploads, and Chromium DevTools Protocol access. Building these
protocols directly would duplicate a mature browser automation runtime and create avoidable race
and compatibility risk.

## Decision

Use the official asynchronous Playwright Python library with its managed Chromium build. Wrap it
behind CEO OS-owned browser engine and transport protocols so no CEO-kernel component imports
Playwright. Prefer role, label, placeholder, text, and test-ID locators; CSS remains an explicit
last DOM-level option. Use a fresh `BrowserContext` for every named isolated session.

Pin Playwright to a compatible minor range and provision Chromium explicitly during development and
container builds. Browser network, filesystem, session-state, effect, cancellation, and output
policies remain CEO OS responsibilities rather than Playwright defaults.

## Consequences

- Browser binaries increase installation and container size.
- Browser versions must stay synchronized with the Python package.
- Deterministic fixture tests can exercise real Chromium instead of mocks alone.
- The provider can later be replaced or extended with controlled CDP attachment without changing
  CEO planning or capability contracts.

The decision follows Playwright's documented isolated browser contexts, locator auto-waiting and
strictness, CDP session support for Chromium, and explicit download lifecycle.
