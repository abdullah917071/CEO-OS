# ADR 0004 — Persistent bounded agent runtime

Status: accepted

## Context

Phase 9 needs dynamic workers, parallelism, messaging, lifecycle controls, and budgets. Embedding
provider logic in the CEO runtime would couple delegation to one model or research implementation.
Process-only workers would also disappear on restart and could not support inspection or audit.

## Decision

Agent definitions, assignments, and messages use normalized tables in the existing SQL database.
A project-owned `WorkerExecutor` protocol separates orchestration from worker implementation. The
runtime validates template bounds before persistence, uses structured assignments and results,
enforces concurrency and timeout budgets, publishes lifecycle events, and owns cancellation.

Phase 9 includes a deterministic research executor strictly for orchestration acceptance. Its data
is labeled simulated. Real model, browser, and integration-backed executors can implement the same
protocol later. No new queue, model framework, database, or third-party dependency is introduced.

## Consequences

- Registry and assignment state survive API restart.
- The CEO kernel depends only on a typed delegation capability.
- Budget and permission expansion is rejected at the boundary.
- In-flight work is process-local and cancelled on shutdown; recovery of unfinished agent
  assignments remains future distributed-runtime work.
