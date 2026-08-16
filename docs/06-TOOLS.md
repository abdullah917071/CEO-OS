# Tools and Capabilities

Tools are deterministic action primitives. Each registers a unique capability name, description, JSON-compatible input schema, risk class, source, and execution implementation. The CEO sees only relevant capability specifications.

The capability registry supports discovery and dispatch. Tool results contain structured output and evidence. Every invocation receives a stable operation idempotency key. Provider adapters must forward it to idempotency-aware APIs or maintain a local deduplication record. Errors are typed and sanitized; timeouts, retries, approval, audit, and rollback metadata are enforced around execution rather than reimplemented by every tool.

Milestone 1 capabilities are `time.now`, `calculator.evaluate`, `notes.add`, `files.mkdir`, `files.write`, `files.read`, and allowlisted `shell.execute`. Files remain inside the configured workspace. The shell has no shell interpolation and only explicitly read-only commands.

MCP tools and native integrations will adapt into the same internal capability contract. A remote tool never bypasses local policy because it arrived through MCP.
