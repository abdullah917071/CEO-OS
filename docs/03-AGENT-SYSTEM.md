# Agent System

The permanent hierarchy begins with CEO and may later include Executive Assistant, Marketing, Social, Sales, Finance, Operations, Technical, Research, and Communications directors. Dynamic workers are created from versioned templates for bounded objectives and terminated after useful knowledge is consolidated.

Every agent definition includes identity, role, allowed capabilities, data scope, model class, runtime/cost budgets, spawn authority, escalation policy, and expected output schema. Workers receive the minimum context needed for their task.

Agents communicate through task assignments and structured results, not shared mutable prompts. A result includes output, evidence, confidence, uncertainty, cost, and any follow-up recommendation. High-impact work uses executor/verifier separation.

Phase 9 implements the first bounded workforce runtime. Agent definitions, assignments, and
messages are persisted in the existing SQL database. Permanent CEO and Research Director records
are seeded idempotently; temporary agents preserve their parent, template/version, role, model
class, capability allowlist, data scope, spawn authority, runtime/cost/concurrency budgets, status,
and termination time.

The runtime owns create, clone, bounded update, pause, resume, terminate, targeted assignment,
parallel delegation, structured messaging, lifecycle events, timeout enforcement, cost enforcement,
and cancellation. Permanent agents cannot be mutated through temporary-agent controls. Requested
capabilities and data scope must be subsets of the selected template; budgets can only be reduced.

`WorkerExecutor` is a provider-neutral contract. Phase 9 ships a deterministic research executor
only to verify orchestration. It returns synthetic comparison fixtures labeled `simulation` and
states that no live sources were queried. Live model/browser/integration-backed workers replace the
executor later without changing the CEO delegation capability or persistence model.

CEO can route the bounded top-ten-competitor acceptance request through
`agents.delegate.research`. The tool partitions items across temporary workers, executes them
concurrently, orders synthesis by the original request, aggregates evidence/confidence/uncertainty/
cost/runtime, and terminates workers after completion. Cross-process queues and recovery of work
that was in-flight during a process crash remain future work.
