# Milestone 15 — Marketing Intelligence Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for the Marketing Intelligence milestone.

Status: implemented and verified on 2026-08-16.

## Verification result

- The full suite passed with 104 tests, including the Marketing Intelligence subsystem (attribution
  funnels, profit diagnostics, creative fatigue analysis, daily snapshots), REST endpoints
  (`/api/v1/intelligence/marketing/*`), Capability Router classification, and task execution acceptance.
- Strict typing passed with 0 errors across 45 Python source files (`uv run mypy`).
- Python lint passed with 0 warnings (`uv run ruff check .`).
- Dashboard unit tests, TypeScript check, and Next.js 16.3.1 production build passed across all 7 routes.
- Docker Compose validation passed (`docker compose config --quiet`).
- End-to-end CEO task acceptance: CEO received natural language request:
  `"Why did profit fall yesterday?"`
  CEO formulated execution plan with `marketing.profit.diagnose`, analyzed the cross-channel funnel
  (Meta Ads spend surge on fatigued creative + landing page bounce spike + refund increase), returned
  a structured root-cause diagnostic report with recommended actions, and finished in `success` state.

## Objective

Deliver the unified Marketing Intelligence and multi-channel attribution subsystem combining Meta,
Google Ecosystem, GA4 Analytics, CRM pipelines, and Sales revenue per `PLANS.md` Section 106 and Section 31.

## Acceptance criteria

- `MarketingIntelligenceIntegration` implements `NativeIntegrationProvider` and registers 4 capability tools:
  - `marketing.profit.diagnose` (R0): Cross-channel root-cause diagnosis answering "Why did profit fall yesterday?".
  - `marketing.attribution.funnel` (R0): 7-stage attribution pipeline (Ad Impressions → Clicks → Sessions → Leads → Orders → Revenue → Profit).
  - `marketing.creatives.analyze` (R0): Creative performance, fatigue scores, and decay status.
  - `marketing.snapshot.get` (R0): Unified daily snapshot combining ad spend, traffic, CRM, and sales.
- `MarketingIntelligenceEngine` computes blended ROAS, CAC, contribution margin, and causal root causes.
- `CapabilityRouter` maps `marketing.` prefix and domain keywords to `integrations`.
- `DeterministicProvider` in `apps/api/src/ceo_os_api/planner.py` parses profit diagnostic, attribution,
  and creative fatigue intents.
- REST endpoints: `GET /api/v1/intelligence/marketing/diagnose`, `GET /api/v1/intelligence/marketing/snapshot`,
  `GET /api/v1/intelligence/marketing/creatives`, `GET /api/v1/intelligence/marketing/attribution`.
- Full regression checks, linting, type checks, and dashboard production build pass.

## Non-goals

- Relying on single-metric isolated platform dashboards instead of synthesized financial attribution.
