# Security

CEO OS treats models, websites, messages, documents, MCP servers, and third-party outputs as untrusted. Authority comes only from the owner, authenticated system policy, and scoped approvals.

Secrets flow from tools to a credential broker and vault; prompts and logs see credential references, never values. Workers use isolated task workspaces, least-privilege credentials, network policy, execution budgets, and explicit capability grants.

All effects produce append-only audit facts: actor, task, capability, arguments with secret redaction, before/after state where applicable, reason, policy decision, result, evidence, and time. Logs must not record hidden model reasoning.

Threat modeling covers prompt injection, confused deputies, credential exfiltration, path traversal, command injection, SSRF, malicious integrations, replay/duplicate effects, supply-chain compromise, and unsafe rollback. Security hardening is continuous; high-value autonomy waits for dedicated Milestone 21 validation.

