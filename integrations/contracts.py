"""Integration contracts, manifests, and provider protocols."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from core.contracts import CapabilitySpec, RiskLevel, Tool


class IntegrationType(StrEnum):
    MCP = "mcp"
    NATIVE = "native"


class IntegrationHealth(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


# ── Typed Exception Hierarchy ───────────────────────────────────────────────


class IntegrationError(Exception):
    """Base error for all integration failures."""


class AuthenticationError(IntegrationError):
    """Raised when authentication or token exchange fails."""


class RateLimitError(IntegrationError):
    """Raised when an integration's configured rate limit is exceeded."""


class IntegrationNotFoundError(IntegrationError):
    """Raised when looking up an unregistered integration."""


# ── Secrets and OAuth Contracts ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SecretReference:
    """Opaque reference to a secret stored in the secret vault."""

    credential_id: str
    name: str
    description: str
    created_at: datetime
    expires_at: datetime | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SecretLease:
    """Authorized temporary lease of a secret value for an integration or tool."""

    credential_id: str
    secret_value: str
    leased_at: datetime
    lease_expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OAuthProfile:
    """Configuration for an OAuth 2.0 PKCE provider."""

    provider_name: str
    client_id_ref: str
    client_secret_ref: str | None
    authorize_url: str
    token_url: str
    scopes: list[str] = field(default_factory=list)
    redirect_uri: str = "http://localhost:8000/api/v1/integrations/oauth/callback"


@dataclass(frozen=True, slots=True)
class OAuthState:
    """In-flight OAuth state tracking for PKCE authorization."""

    state_token: str
    provider_name: str
    code_verifier: str
    code_challenge: str
    redirect_uri: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class OAuthToken:
    """Opaque OAuth 2.0 token record referenced by the secret vault."""

    credential_id: str
    provider_name: str
    token_type: str
    access_token_ref: str
    refresh_token_ref: str | None
    scopes: list[str]
    expires_at: datetime | None
    issued_at: datetime


# ── Manifest and Status ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class IntegrationManifest:
    """Declarative metadata for an integration package."""

    name: str
    version: str
    description: str
    integration_type: IntegrationType
    domain: str = "integrations"
    capabilities: list[CapabilitySpec] = field(default_factory=list)
    required_credentials: list[str] = field(default_factory=list)
    rate_limits: dict[str, Any] = field(default_factory=dict)
    risk_ceiling: RiskLevel = RiskLevel.HARMLESS_WRITE
    oauth_profile: OAuthProfile | None = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class IntegrationStatus:
    """Runtime snapshot of an integration's state."""

    name: str
    version: str
    description: str
    integration_type: str
    health: str
    tool_count: int
    risk_ceiling: str
    enabled: bool
    domain: str = "integrations"
    connected_at: datetime | None = None
    error: str | None = None


class IntegrationProvider(Protocol):
    """Contract that every integration — MCP or native — must satisfy."""

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    def status(self) -> IntegrationStatus: ...

    def tools(self) -> list[Tool]: ...
