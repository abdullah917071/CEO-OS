# Milestone 14 — Meta Integration Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for the Meta Marketing API integration milestone.

Status: implemented and verified on 2026-08-16.

## Verification result

- The full suite passed with 97 tests, including the Meta Marketing API integration
  (Ad Accounts, Campaigns, Ad Sets, Creatives, Ads, Insights, and Reporting), REST endpoints (`/api/v1/meta/*`),
  Capability Router classification, and task execution acceptance.
- Strict typing passed with 0 errors across 45 Python source files (`uv run mypy`).
- Python lint passed with 0 warnings (`uv run ruff check .`).
- Dashboard unit tests, TypeScript check, and Next.js 16.3.1 production build passed across all 7 routes.
- Docker Compose validation passed (`docker compose config --quiet`).
- End-to-end CEO task acceptance: CEO received natural language request:
  `"Create a draft ₹800/day campaign targeting Entrepreneurs using creative Launch Promo."`
  CEO formulated execution plan with `meta.campaigns.create`, `meta.creatives.create`, and `meta.adsets.create`,
  created the draft campaign with ₹800 daily budget, configured creative copy and headline, established audience targeting,
  and returned structured evidence in terminal `success` state.

## Objective

Deliver the official Meta Marketing API integration providing programmatic advertising operations
(Facebook, Instagram, Audience Network) rather than brittle browser automation, per `PLANS.md` Section 105.

## Acceptance criteria

- `MetaMarketingIntegration` implements `NativeIntegrationProvider` and registers 13 typed capability tools:
  - Accounts: `meta.accounts.list` (R0), `meta.accounts.get` (R0)
  - Campaigns: `meta.campaigns.list` (R0), `meta.campaigns.create` (R2), `meta.campaigns.update` (R2)
  - Ad Sets: `meta.adsets.list` (R0), `meta.adsets.create` (R2)
  - Creatives: `meta.creatives.list` (R0), `meta.creatives.create` (R2)
  - Ads: `meta.ads.list` (R0), `meta.ads.create` (R2)
  - Insights & Reporting: `meta.insights.get` (R0), `meta.reporting.campaign` (R0)
- `MetaClient` provides high-fidelity simulation store and live Graph API client structures supporting
  both INR (`₹`) and USD currencies.
- `CapabilityRouter` maps `meta.` capabilities and domain keywords to `integrations`.
- `DeterministicProvider` in `apps/api/src/ceo_os_api/planner.py` parses campaign creation and reporting intents.
- REST endpoints: `GET/POST /api/v1/meta/campaigns`, `GET/POST /api/v1/meta/adsets`, `GET/POST /api/v1/meta/creatives`,
  `GET/POST /api/v1/meta/ads`, `GET /api/v1/meta/accounts`, `GET /api/v1/meta/insights`, `GET /api/v1/meta/reports/{id}`.
- Full regression checks, linting, type checks, and dashboard production build pass.

## Non-goals

- Incurring live Meta ad spend during automated test runs.
- Relying on web scraping or browser UI clicks when official Graph API interfaces exist.
