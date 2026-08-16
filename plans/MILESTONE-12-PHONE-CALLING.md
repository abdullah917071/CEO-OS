# Milestone 12 — Phone Calling Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its phone calling / telephony milestone.

Status: implemented and verified on 2026-08-16.

## Verification result

- The full suite passed with 86 tests, including Telephony manifest/tools (`telephony.call.outbound`,
  `telephony.call.status`, `telephony.call.terminate`), multi-turn simulated telephone dialogues
  (opening hours and restaurant table reservations), E.164 and prefix policy enforcement, call
  idempotency, automatic episodic memory recording in `MemoryService`, capability router domain
  classification, and REST endpoints (`/api/v1/telephony/*`).
- Strict typing passed with 0 errors across 45 Python source files (`uv run mypy`).
- Python lint passed with 0 warnings (`uv run ruff check .`).
- Dashboard unit tests, TypeScript check, and Next.js 16.3.1 production build passed across all 7 routes.
- Docker Compose validation passed (`docker compose config --quiet`).
- End-to-end CEO task acceptance: CEO received natural language calling request ("Call +1-415-555-0100
  and ask whether they're open tomorrow."), formulated execution plan with `telephony.call.outbound`,
  conducted conversation, extracted store hours (11:00 AM to 10:00 PM), wrote episodic memory, and
  returned structured evidence and terminal `success`.

## Objective

Build provider-neutral telephony integration for CEO OS, separating carrier providers (Twilio, SIP,
deterministic simulation) from call management, conversation state machine, live transcripts,
structured summaries, and long-term episodic memory retention.

## Acceptance criteria

- `TelephonyIntegration` implements `NativeIntegrationProvider` and registers 3 typed capability tools:
  - `telephony.call.outbound` (R2 - External Communication)
  - `telephony.call.status` (R0 - Read)
  - `telephony.call.terminate` (R2 - External Communication)
- `DeterministicTelephonyProvider` generates multi-turn conversational dialogue matching stated objectives
  (e.g., store hours, restaurant bookings) with millisecond speaker timestamps, duration calculations,
  token-based cost tracking, and structured data extraction.
- `CallManager` manages active call registry, enforces policy constraints (E.164 format, allowed prefixes,
  timeout bounds), and automatically commits call summaries and extracted data into episodic memory.
- `CapabilityRouter` domain keywords and prefixes map `telephony.*` capabilities to `integrations`.
- `DeterministicProvider` in `apps/api/src/ceo_os_api/planner.py` recognizes natural language calling
  prompts and formulates plans with `telephony.call.outbound`.
- REST endpoints: `POST /api/v1/telephony/calls`, `GET /api/v1/telephony/calls`, `GET /api/v1/telephony/calls/{call_id}`,
  `POST /api/v1/telephony/calls/{call_id}/terminate`.
- Full regression checks, linting, type checks, and dashboard production build pass.

## Non-goals

- Incurring live telecom carrier billing during automated headless CI.
- Automated unsolicited outbound marketing calls or unconstrained robocalling.
