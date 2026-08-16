# Event System

Events make execution observable and trigger later automation. Names use a versioned domain convention such as `task.created`, `task.step.completed`, `agent.failed`, or `integration.connected`.

Every event has an event ID, type, schema version, occurrence time, producer, task/correlation IDs, optional causation ID, and typed payload. Events contain operational decisions and results, not private chain-of-thought or secrets.

PostgreSQL remains authoritative. WebSocket events are currently best-effort process-local notifications; clients reconnect and query REST. LangGraph checkpoints are durable execution state but not a substitute for domain events. A later milestone introduces a transactional outbox and Redis Streams distribution with consumer groups and replay bounds.

Triggers consume durable events idempotently. An event indicating provider acceptance is not necessarily proof that the external business outcome completed.
