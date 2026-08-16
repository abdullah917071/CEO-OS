# Milestone 11 — Google Ecosystem Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its Google ecosystem milestone.

Status: implemented and verified on 2026-08-16.

## Verification result

- The full suite passed with 77 tests, including Gmail search/read/draft/send, Calendar event
  listing/creation/update/freebusy, Contacts search/details, Drive file search/read/creation,
  Places/Maps search/details, Google Analytics GA4 metrics reporting, YouTube video search and
  channel metrics, Capability Router domain routing, and CEO task execution acceptance.
- Strict typing passed with 0 errors across 45 Python source files (`uv run mypy`).
- Python lint passed with 0 warnings (`uv run ruff check .`).
- Dashboard unit tests, TypeScript check, and Next.js 16.3.1 production build passed across all 7 routes.
- Docker Compose validation passed (`docker compose config --quiet`).
- End-to-end CEO task acceptance: CEO received natural language objectives ("Check my emails about budget"
  and "Find restaurant named Osteria Bella"), formulated structured execution plans, executed Google
  ecosystem tools (`google.gmail.search` and `google.places.search`), and returned structured evidence
  and outcomes.

## Objective

Integrate the comprehensive Google Ecosystem (Gmail, Calendar, Contacts, Drive, Places/Maps,
Analytics, YouTube) into CEO OS via the Native Integration SDK, enabling personal productivity and
business operation automation through typed, risk-classified capabilities and credential-safe reference
isolation.

## Acceptance criteria

- `GoogleEcosystemIntegration` implements `NativeIntegrationProvider` and registers 17 typed tools:
  - Gmail: `google.gmail.search` (R0), `google.gmail.read` (R0), `google.gmail.draft` (R1), `google.gmail.send` (R2)
  - Calendar: `google.calendar.list` (R0), `google.calendar.create_event` (R2), `google.calendar.update_event` (R2), `google.calendar.freebusy` (R0)
  - Contacts: `google.contacts.search` (R0), `google.contacts.get` (R0)
  - Drive: `google.drive.search` (R0), `google.drive.read` (R0), `google.drive.create` (R1)
  - Places / Maps: `google.places.search` (R0), `google.places.details` (R0)
  - Analytics: `google.analytics.report` (R0)
  - YouTube: `google.youtube.search` (R0), `google.youtube.metrics` (R0)
- `GoogleClient` handles OAuth token / API key leasing via `SecretBroker` and provides high-fidelity
  simulation fallbacks when offline or credentials are not supplied.
- `CapabilityRouter` domain keywords and prefixes map `google.*` capabilities to appropriate domains
  (`integrations`, `files`, `system`).
- `DeterministicProvider` in `apps/api/src/ceo_os_api/planner.py` recognizes and routes user queries
  for emails, calendars, places, drive documents, analytics, and videos.
- All capabilities appear in `/api/v1/capabilities` and `/api/v1/integrations`.
- Full regression checks, linting, type checks, and dashboard production build pass.

## Non-goals

- Live user account OAuth sign-in popups during automated headless CI.
- Sending unverified emails to external recipients without R2 policy evaluation.
