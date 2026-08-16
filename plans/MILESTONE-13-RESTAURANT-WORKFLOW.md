# Milestone 13 — Restaurant Booking Workflow Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for the multi-service Restaurant Booking Workflow milestone.

Status: implemented and verified on 2026-08-16.

## Verification result

- The full suite passed with 91 tests, including the end-to-end Restaurant Booking Workflow
  (`workflow.restaurant.book`), Places discovery, Telephony outbound calling, Google Calendar
  scheduling, Episodic Memory recording, and Executive Reporting.
- Strict typing passed with 0 errors across 45 Python source files (`uv run mypy`).
- Python lint passed with 0 warnings (`uv run ruff check .`).
- Dashboard unit tests, TypeScript check, and Next.js 16.3.1 production build passed across all 7 routes.
- Docker Compose validation passed (`docker compose config --quiet`).
- End-to-end CEO task acceptance: CEO received natural language request:
  `"Find restaurant named Osteria Bella, call them to book a table for 4 at 7:00 PM tonight, add to calendar, and report back."`
  CEO formulated execution plan with `workflow.restaurant.book`, discovered the restaurant and phone number,
  placed simulated phone call and confirmed reservation, created Google Calendar event, recorded episodic memory,
  and returned structured evidence across all 5 stages in terminal `success` state with zero manual intervention.

## Objective

Deliver the first composite multi-subsystem workflow combining Google Places, Telephony, Google Calendar,
Memory, and Reporting into an autonomous pipeline per `PLANS.md` Section 104 and Section 25.

## Acceptance criteria

- `RestaurantWorkflowIntegration` implements `NativeIntegrationProvider` and registers `workflow.restaurant.book` (R2 - External Communication).
- `RestaurantBookingWorkflow` executes 5-stage autonomous pipeline:
  1. **Places**: Search restaurant name, resolve address, rating, and phone number (`+1-415-555-7890`).
  2. **Telephony**: Outbound phone call with dialogue to confirm table reservation, party size, time, and name.
  3. **Calendar**: Schedule confirmed dinner event with address, party details, and attendee info.
  4. **Memory**: Save episodic memory with reservation attributes and telephone provenance.
  5. **Report**: Compile executive summary and full 5-stage evidence trail.
- `CapabilityRouter` domain keywords and `workflow.` prefix map capabilities to `integrations`.
- `DeterministicProvider` in `apps/api/src/ceo_os_api/planner.py` recognizes restaurant reservation prompts
  and generates execution plans targeting `workflow.restaurant.book`.
- REST endpoints: `POST /api/v1/workflows/restaurant-booking`.
- Full regression checks, linting, type checks, and dashboard production build pass.

## Non-goals

- Incurring live restaurant cancellation fees or carrier charges during automated test runs.
- Hardcoded brittle web-scraping when official API and telephony capabilities exist.
