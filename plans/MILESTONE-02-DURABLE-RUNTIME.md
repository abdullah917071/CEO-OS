# Milestone 2 — Durable Runtime Execution Plan

Status: implemented and verified on 2026-08-15.

`PLANS.md` is the immutable governing roadmap. This file expands its Milestone 2 requirements into implementation decisions and acceptance tests.

## Objective

Replace the synchronous in-process Phase 1 loop with a LangGraph workflow whose state is checkpointed after planning and every completed step. Tasks must survive process loss, reject duplicate submissions, recover abandoned work through leases, retry transient failures with bounded backoff, and support cooperative pause, resume, and cancel.

## Design decisions

- PostgreSQL uses `AsyncPostgresSaver` in normal deployments; async SQLite uses `AsyncSqliteSaver` for local fallback and tests. Both are behind a checkpointer factory.
- The task UUID is the LangGraph `thread_id`. PostgreSQL task/step records remain the query and audit projection; LangGraph checkpoints are execution state, not business history.
- `POST /chat/messages` accepts an optional idempotency key and returns after task creation. A background runner acquires a lease and executes the graph.
- A unique idempotency key returns the original task and never creates or executes a duplicate.
- Step records are unique by task and plan index. Completed records are replayed into graph state without re-executing the tool.
- Each tool effect uses a stable key derived from task ID, step index, capability, and canonical arguments. Retries read the existing completed step before invoking the tool.
- LangGraph applies three attempts with exponential backoff to transient execution failures. Validation, permission, and unknown-capability failures are permanent.
- Pause and cancel requests are persisted control flags. A control-gate node checks them between steps; pause uses a LangGraph interrupt and resume uses `Command(resume=True)`. Cancellation routes to a terminal cancelled node.
- A database lease has an owner and expiry. Only its owner may renew/release it. Startup recovery queues all non-terminal tasks whose lease is absent or expired.
- API lifecycle operations are `POST /tasks/{id}/pause`, `/resume`, and `/cancel`; invalid terminal transitions return conflict.

## Implementation sequence

1. Add LangGraph/checkpointer dependencies and durable task/step schema fields.
2. Add repository transactions for idempotent creation, state transitions, step evidence, controls, leases, and recovery queries.
3. Build and compile the execution graph with planning, control gate, execution, routing, and terminal nodes.
4. Add the background runner and startup recovery service.
5. Change chat submission to return accepted work and add pause/resume/cancel endpoints.
6. Update the dashboard to expose lifecycle controls and refresh from events.
7. Add migrations/bootstrap compatibility, tests, and operational documentation.

## Acceptance tests

- A multi-step task stores completed step records and checkpoints; resumption does not rerun completed file writes.
- A simulated transient tool failure retries and succeeds within the configured limit; a permanent error fails immediately.
- Duplicate idempotency keys return one task and one set of effects.
- Pause reaches `waiting`, resume completes from the same thread, and cancel reaches `cancelled` without starting another step.
- An expired lease is recoverable; an active lease prevents a second runner.
- Restart recovery resumes non-terminal work from its last checkpoint.
- Existing Milestone 1 capability, path-safety, API, and dashboard behavior remains green.
