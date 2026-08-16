# ADR 0002 — Cua Driver Vision Runtime

Status: accepted

Date: 2026-08-15

## Context

Milestone 6 needs a visual and action layer for native, canvas, and other non-semantic interfaces.
The project already owns task, permission, cancellation, and capability abstractions and should not
duplicate a general cross-platform desktop driver.

## Decision

Use the typed `cua-driver` Python SDK through a project-owned adapter. CEO OS owns the driver for the
API lifespan and defaults to window-scoped capture with effects disabled. The adapter exposes an
intentionally smaller surface than Cua Driver: status, window discovery/capture, and bounded actions.
It does not expose generic `call_tool`, unrestricted mode, desktop targeting, or existing-profile
attachment.

CEO OS continues to enforce its own capability risk policy, exact target allowlist, cancellation,
idempotency, evidence, and independent postconditions. Cua Driver's permission and verification
results are treated as additional enforcement/evidence, not replacements.

## Consequences

- Cua Driver becomes a version-bounded runtime dependency and the old project-specific Swift helper
  remains available as the deterministic Accessibility tier until migration is separately planned.
- macOS live operation requires Screen Recording and Accessibility grants associated with the
  responsible host identity.
- Unit and contract tests run against a fake adapter; live native validation is environment-gated.
