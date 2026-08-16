# Task Runtime

Every meaningful request becomes a persisted task. A task records owner, objective, success conditions, priority, status, plan, workers, attempts, evidence, outputs, errors, costs, and timestamps.

Canonical states are `queued`, `planning`, `running`, `waiting`, `blocked`, `retrying`, `needs_approval`, `success`, `partial_success`, `failed`, and `cancelled`. State changes emit events and are validated by the runtime.

Milestone 2 executes the plan as a LangGraph state graph. Planning and every completed step are checkpointed under a thread ID equal to the task UUID. PostgreSQL uses the async production checkpointer; SQLite and in-memory savers support local development and tests. Durable step records preserve arguments, attempts, output, evidence, errors, and a stable operation idempotency key.

Submission returns accepted work while a leased background runner executes it. A unique request idempotency key returns the original task. Leases have owners and expirations, are renewed during execution, and make abandoned non-terminal work eligible for startup recovery. Transient connection/time-out failures receive three bounded exponential-backoff attempts; validation and permission failures are not retried.

Pause and cancel are cooperative at step boundaries. Pause persists a control request and creates a LangGraph interrupt; resume uses the same thread and `Command(resume=True)`. Cancel routes to a terminal state without starting another step. Completed tool effects receive stable idempotency keys so providers can deduplicate retries.

A task becomes successful only when its success conditions have evidence. A tool returning without error is not sufficient. Partial success preserves completed evidence and identifies unmet conditions; retries must never blindly repeat non-idempotent effects.
