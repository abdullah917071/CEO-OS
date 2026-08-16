# Architecture

## Logical flow

```text
Owner channels -> API -> CEO kernel -> task runtime -> agent/model router
                                      -> capability router -> tools/integrations
                                      -> policy/audit/events
                                      -> memory/context compiler
```

The CEO kernel owns intent, objectives, success conditions, strategy, and delegation. It does not import Meta, browser, telephony, model-provider, or operating-system SDKs. Those implementations register typed capabilities behind stable contracts.

## Runtime boundaries

- FastAPI is the control-plane API and WebSocket event endpoint.
- PostgreSQL is the system of record; pgvector is the initial semantic index.
- Redis supports ephemeral coordination, caching, streams, and presence, but never authoritative task history.
- Next.js is the owner dashboard; it communicates only through versioned API/event contracts.
- LangGraph enters in Milestone 2 for workflows that require durable graph state. Simple deterministic execution remains custom code.
- Local files are initial object/workspace storage; an S3-compatible adapter may replace them later.

## Dependency rule

Dependencies point inward: provider adapters depend on domain contracts. Domain contracts never depend on adapters. Cross-subsystem communication uses typed commands, results, and domain events rather than direct database-table coupling.

## Decisions

Python/FastAPI own orchestration; TypeScript/Next.js own UI; REST handles commands and queries; WebSocket carries transient live updates. PostgreSQL and Redis are the only Phase 0 data services. Any new framework or datastore requires a documented decision and a demonstrated gap.

