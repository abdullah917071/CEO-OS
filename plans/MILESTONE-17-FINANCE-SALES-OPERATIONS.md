# Milestone 17 — Finance + Sales + Operations Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for the Finance + Sales + Operations (Executive Business Operating System) milestone.

Status: implemented and verified on 2026-08-16.

## Verification result

- The full test suite passed with 123 tests, including the Business Executive Intelligence subsystem
  (financial runway modeling, capital allocation affordability simulation, accounts receivable
  tracking, SaaS subscription alerts, sales pipeline lifecycle and stage tracking, operational
  fulfillment health, low-stock inventory alerts, and multi-department executive briefings), REST
  endpoints (`/api/v1/intelligence/business/*`), Capability Router classification, and task execution
  acceptance.
- Python lint passed with 0 warnings (`uv run ruff check .`).
- Type checks passed cleanly (`uv run mypy`).
- Dashboard unit tests, TypeScript check, and Next.js 16.3.1 production build passed across all routes.
- Docker Compose validation passed (`docker compose config --quiet`).
- End-to-end CEO task acceptance:
  1. CEO received natural language request: `"CEO, what's happening?"`
     CEO formulated execution plan with `business.executive.overview`, synthesized multi-department
     state (Revenue +11%, Meta ROAS 3.4x, Google CPA +19%, 2 overdue invoices, ₹1,200 hosting increase,
     developer checkout update, executive call at 3:30), returned structured evidence, and finished in
     `success` state.
  2. CEO received natural language request: `"Can we afford another ₹2 lakh advertising push?"`
     CEO formulated execution plan with `business.finance.affordability`, simulated runway impact
     (remaining runway 7.4 months, cash cushion ₹16.4L, breakeven at 23 units), returned `AFFORDABLE`
     verdict with capital allocation recommendation, and finished in `success` state.

## Objective

Deliver the provider-neutral Business Operating System uniting Finance, Sales, Operations, and
Executive Briefings per `PLANS.md` Section 108, Section 36 (Sales Agent), Section 37 (Finance Agent),
Section 38 (Operations Agent), and Section 114 (The Finished Product).

## Acceptance criteria

- `BusinessIntelligenceIntegration` implements `NativeIntegrationProvider` and registers 8 capability tools:
  - `business.executive.overview` (R0): Synthesize executive status report answering "CEO, what's happening?".
  - `business.finance.overview` (R0): Get consolidated financial metrics, cash balance, profit, receivables.
  - `business.finance.affordability` (R0): Capital allocation and runway forecasting (e.g. ad push spend).
  - `business.finance.invoices` (R0): List billing invoices and track unpaid or overdue client balances.
  - `business.sales.pipeline` (R0): Sales pipeline summary with stages, weighted forecast, and win rates.
  - `business.sales.deals` (R0): List sales opportunities filtered by lifecycle stage.
  - `business.operations.health` (R0): Operational health, order fulfillment rate, and exceptions.
  - `business.operations.inventory` (R0): Inspect inventory stock levels and reorder trigger alerts.
- `BusinessExecutiveEngine` executes financial runway algorithms, capital affordability simulations,
  deal pipeline qualification, and operational exception aggregation.
- `CapabilityRouter` maps `business.` prefix and domain keywords (`finance`, `invoice`, `receivables`,
  `subscription`, `afford`, `pipeline`, `inventory`, `runway`, `overview`, `deal`, `briefing`, `happening`,
  `business`, `executive`, `status`) to `integrations`.
- `DeterministicProvider` in `apps/api/src/ceo_os_api/planner.py` parses briefing and affordability intents.
- REST endpoints: `GET /api/v1/intelligence/business/overview`, `GET /api/v1/intelligence/business/finance`,
  `GET /api/v1/intelligence/business/finance/affordability`, `GET /api/v1/intelligence/business/finance/invoices`,
  `GET /api/v1/intelligence/business/sales/pipeline`, `GET /api/v1/intelligence/business/sales/deals`,
  `GET /api/v1/intelligence/business/operations/health`, `GET /api/v1/intelligence/business/operations/inventory`.
- Full regression checks, linting, type checks, and dashboard production build pass.

## Non-goals

- Binding financial forecasting to a single accounting provider SDK instead of typed contracts.
