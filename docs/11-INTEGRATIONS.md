# Integrations

An integration package contains a manifest, authentication adapter, client, schemas, capability tools, normalized errors, tests, and operator documentation. Its manifest declares version, capabilities, required credentials/scopes, rate limits, risk, webhook events, and health state.

Official APIs are preferred over browser automation. OAuth tokens and API keys are obtained through a credential broker by reference. Provider-specific objects are normalized at the boundary while raw provider identifiers remain available for audit and reconciliation.

MCP servers are discovered and adapted through a registry, but MCP is a transport/interface standard rather than the domain architecture. Installation cannot automatically authorize capabilities.

Milestone 10 proves extensibility by installing a new MCP or native integration without modifying the CEO kernel. Meta, telephony, and Google implementations are explicitly out of Phase 1.

