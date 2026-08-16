# CEO Kernel

The CEO kernel converts an owner message plus a compiled context pack into a structured objective and execution strategy. Its stable inputs are the message, identity, relevant goals/memories/entities, system state, available agents/capabilities, and applicable policies.

Its output is an execution plan containing an objective, explicit success conditions, and goal-oriented steps. Every step names a capability and typed arguments; provider implementation details remain outside the plan.

## Responsibilities

- Clarify intent and choose a deterministic fast path when possible.
- Decide whether to answer, execute directly, delegate, request approval, or refuse.
- Load only relevant capabilities and context.
- Track uncertainty, evidence requirements, budgets, and completion criteria.
- Synthesize worker results into a concise owner response.

## Non-responsibilities

The kernel does not hold credentials, execute shell commands, click interfaces, call provider APIs, persist raw memories, or contain specialist business logic. Those belong to tools, integrations, memory, and agents.

Milestone 1 uses a deliberately small deterministic planner behind the model-provider contract. Later hosted and local providers implement the same contract, selected by role, cost, latency, availability, and privacy policy.

