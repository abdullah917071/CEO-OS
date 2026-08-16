# Dashboard

The dashboard is the owner’s command center. Its eventual areas are CEO chat, goals, projects, agents, tasks, automations, memory, business domains, calls/messages/calendar, files, integrations, skills, reports, activity, approvals, system, and settings.

Dashboard V1 provides a focused owner console with shared navigation for Chat, Tasks, Activity,
Agents, Memory, Integrations, and Settings. Chat submits normal durable tasks. Task cards expose the
objective, lifecycle, plan, result, evidence, errors, timestamps, and only the controls valid for
the current state. An accepted request is explicitly described as queued rather than completed.

REST is used for commands and authoritative queries; WebSocket events trigger near-real-time REST
refresh. Connection and reconnection both refresh state because events may be missed. Activity has
a bounded process-local REST snapshot and says clearly that it resets on API restart; durable audit
history and Redis distribution remain later work.

Memory supports recent active records and semantic search with provenance and confidence. Agents
shows only the implemented CEO runtime and labels worker orchestration as Phase 9. Integrations
shows the live typed capability registry and labels external/MCP installation as Phase 10. Settings
is deliberately read-only and presents readiness plus computer, browser, vision, and voice status
without credentials or permission-broadening controls.

Later dashboard work includes change-objective/take-over controls, the live agent map, computer
view, memory correction, approvals, cost, global stop, authentication, and durable activity/audit
history.
