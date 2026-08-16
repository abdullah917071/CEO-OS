# Milestone 10 — Integration Platform Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its integration platform milestone.

Status: implemented and verified on 2026-08-16.

## Verification result

- The full suite passed with 70 tests, including dynamic MCP installation, live capability discovery,
  task execution with evidence, Secret Vault storage, credential leasing and log masking, OAuth 2.0
  PKCE authorization and token lifecycle, domain-based capability routing, and native rate limiting.
- Strict typing passed with 0 errors across 45 Python source files (`uv run mypy`).
- Python lint passed with 0 warnings (`uv run ruff check .`).
- Dashboard unit tests, TypeScript check, and Next.js 16.3.1 production build passed across all routes
  including the enhanced Integrations page.
- Docker Compose validation passed (`docker compose config --quiet`).
- Dynamic integration acceptance: installed an authenticated native integration at runtime without
  modifying CEO core, verified discovery via `/api/v1/capabilities`, executed a durable CEO task
  yielding structured evidence, and uninstalled it cleanly.

## Objective

Deliver an extensible integration platform for CEO OS where external tools and MCP servers can be
installed, discovered, authenticated, and executed dynamically without modifying the CEO core kernel.
Manage credentials safely through reference isolation and a Secret Broker, handle OAuth 2.0 PKCE
flows, and route capabilities efficiently using a domain classifier.

## Acceptance criteria

- An MCP stdio client connects to external tool servers, extracts structured schemas, executes tools
  with timeouts and error handling, and maps risk classes up to configurable ceilings.
- An integration registry manages native and MCP providers with dynamic install, uninstall, and
  synchronization listeners that update the live `CapabilityRegistry` without restarting the server.
- A native integration SDK provides typed error classes (`IntegrationError`, `AuthenticationError`,
  `RateLimitError`), token bucket rate limiting, and credential resolution.
- A Secret Broker and Vault store sensitive values under opaque credential IDs, lease them to authorized
  components, and mask raw secret values in strings, task logs, and API payloads.
- An OAuth Manager supports RFC 7636 PKCE flows, authorization URL generation, state tracking, and
  secure token storage in the Secret Vault.
- A Capability Router classifies queries into domains (`system`, `files`, `calc`, `memory`, `agents`,
  `computer`, `browser`, `vision`, `voice`, `integrations`) and filters tool sets to avoid prompt bloat.
- REST endpoints support dynamic MCP installation (`POST /api/v1/integrations/mcp`), uninstallation
  (`DELETE /api/v1/integrations/{name}`), secret management (`/api/v1/secrets`), OAuth authorization
  and callbacks (`/api/v1/integrations/oauth/*`), and capability routing (`/api/v1/capabilities/route`).
- The Integrations dashboard command center includes an MCP installation form, status monitors,
  secret reference view (redacted), OAuth status, and domain-grouped capabilities.
- Acceptance test scenario passes: install a new integration at runtime without modifying CEO core;
  CEO discovers and executes it.

## Non-goals

- Live third-party provider accounts (Meta Ads, Google Marketing, Twilio) are deferred to their
  respective milestones (Milestones 11–15).
- Exposing raw secret values in dashboard UI, logs, prompts, or API responses is strictly prohibited.
