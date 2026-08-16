# Testing

Testing is layered: pure unit tests for contracts/planning/tools, repository tests, API tests, provider contract tests, container integration tests, dashboard component/build tests, and later end-to-end agent evaluations.

Tool safety tests cover arithmetic syntax rejection, path traversal, command allowlists, timeouts, size limits, and evidence. Task tests cover lifecycle transitions, unsupported requests, failure preservation, and history. WebSocket tests cover connect and lifecycle publication.

Milestone 1 acceptance includes the complete `project-x` filesystem scenario in a temporary workspace. Tests must not access the real home directory, external accounts, or paid models.

Later a sandbox supplies fake bank, ads, email, calendar, CRM, filesystem, and phone counterparts. Evaluation tracks success, unnecessary actions, cost, latency, policy violations, and evidence quality; regression thresholds gate releases.

