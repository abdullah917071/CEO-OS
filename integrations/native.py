"""Native integration SDK and built-in example integrations."""

from __future__ import annotations

import logging
import platform
import socket
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from integrations.contracts import (
    AuthenticationError,
    IntegrationHealth,
    IntegrationManifest,
    IntegrationStatus,
    IntegrationType,
    RateLimitError,
)
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)


# ── Rate Limiter ────────────────────────────────────────────────────────────


class TokenBucketRateLimiter:
    """Thread-safe token bucket rate limiter for native integrations."""

    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10) -> None:
        self.capacity = float(burst_limit)
        self.tokens = float(burst_limit)
        self.fill_rate = float(requests_per_minute) / 60.0
        self.last_update = time.monotonic()

    def acquire(self) -> bool:
        """Attempt to acquire 1 token. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


# ── Provider Base Class ─────────────────────────────────────────────────────


class NativeIntegrationProvider:
    """Base class for non-MCP integrations.

    Subclasses define :meth:`manifest` and :meth:`build_tools`.
    The base class manages health, lifecycle, rate limiting, and status bookkeeping.
    """

    def __init__(self, secret_broker: SecretBroker | None = None) -> None:
        self._secret_broker = secret_broker
        self._tools: list[Tool] = []
        self._health = IntegrationHealth.UNKNOWN
        self._connected_at: datetime | None = None
        self._error: str | None = None
        self._rate_limiter: TokenBucketRateLimiter | None = None

    @property
    def secret_broker(self) -> SecretBroker | None:
        return self._secret_broker

    def manifest(self) -> IntegrationManifest:
        """Return the declarative manifest for this integration."""
        raise NotImplementedError

    def build_tools(self) -> list[Tool]:
        """Construct the tool objects this integration provides."""
        raise NotImplementedError

    def check_rate_limit(self) -> None:
        """Enforce rate limits declared in the manifest."""
        if self._rate_limiter and not self._rate_limiter.acquire():
            manifest = self.manifest()
            raise RateLimitError(
                f"Rate limit exceeded for integration '{manifest.name}'. "
                f"Configured limit: {manifest.rate_limits.get('requests_per_minute', 60)}/min"
            )

    async def connect(self) -> None:
        try:
            manifest = self.manifest()
            rpm = manifest.rate_limits.get("requests_per_minute")
            burst = manifest.rate_limits.get("burst_limit", 10)
            if rpm:
                self._rate_limiter = TokenBucketRateLimiter(int(rpm), int(burst))

            # Verify required credentials exist if secret broker is present
            if self._secret_broker and manifest.required_credentials:
                for cred_id in manifest.required_credentials:
                    if self._secret_broker.get_reference(cred_id) is None:
                        raise AuthenticationError(
                            f"Missing required credential reference: {cred_id}"
                        )

            self._tools = self.build_tools()
            self._health = IntegrationHealth.HEALTHY
            self._connected_at = datetime.now(UTC)
            self._error = None
        except Exception as exc:
            self._health = IntegrationHealth.UNAVAILABLE
            self._error = str(exc)
            logger.error("Failed to connect native integration: %s", exc)

    async def disconnect(self) -> None:
        self._tools = []
        self._health = IntegrationHealth.UNAVAILABLE
        self._connected_at = None

    def status(self) -> IntegrationStatus:
        manifest = self.manifest()
        return IntegrationStatus(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            integration_type=manifest.integration_type,
            health=self._health,
            tool_count=len(self._tools),
            risk_ceiling=manifest.risk_ceiling,
            enabled=manifest.enabled,
            domain=manifest.domain,
            connected_at=self._connected_at,
            error=self._error,
        )

    def tools(self) -> list[Tool]:
        return list(self._tools)


# ── Built-in Integrations ───────────────────────────────────────────────────


class SystemInfoTool:
    """Read-only tool that returns host platform information."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="system_info.platform",
            description="Return host platform, Python version, hostname, and workspace path",
            input_schema={},
            risk=RiskLevel.READ,
            source="integration:system_info",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        info = {
            "system": platform.system(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": socket.gethostname(),
            "workspace": str(self._workspace_root),
        }
        return ToolResult(info, [f"Platform: {info['system']} {info['platform']}"])


class SystemInfoIntegration(NativeIntegrationProvider):
    """Built-in example integration: read-only host platform information."""

    def __init__(self, workspace_root: Path) -> None:
        super().__init__()
        self._workspace_root = workspace_root

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="system_info",
            version="0.1.0",
            description="Read-only host platform information",
            integration_type=IntegrationType.NATIVE,
            domain="system",
            risk_ceiling=RiskLevel.READ,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [SystemInfoTool(self._workspace_root)]


class AuthenticatedMockWeatherTool:
    """Sample authenticated tool that verifies credentials via SecretBroker."""

    def __init__(self, provider: NativeIntegrationProvider, api_key_ref: str) -> None:
        self._provider = provider
        self._api_key_ref = api_key_ref

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="weather.get_forecast",
            description="Get current weather and forecast for a specified city",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name"}},
                "required": ["city"],
            },
            risk=RiskLevel.READ,
            source="integration:mock_weather",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        self._provider.check_rate_limit()

        # Validate secret lease if broker is available
        if self._provider.secret_broker:
            # Lease credential value to verify validity
            lease = self._provider.secret_broker.lease_secret(
                self._api_key_ref, "weather.get_forecast"
            )
            # Secret is used internally; never returned in output
            assert lease.secret_value is not None

        city = str(arguments.get("city", "San Francisco"))
        output = {
            "city": city,
            "condition": "Sunny",
            "temperature_f": 72,
            "humidity_percent": 45,
            "source": "MockWeatherProvider",
        }
        return ToolResult(output, [f"Forecast for {city}: Sunny, 72°F"])


class MockWeatherIntegration(NativeIntegrationProvider):
    """Reference authenticated native integration requiring an API token from SecretBroker."""

    def __init__(
        self,
        api_key_ref: str = "cred_weather_api",
        secret_broker: SecretBroker | None = None,
        requests_per_minute: int = 60,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._api_key_ref = api_key_ref
        self._rpm = requests_per_minute

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="mock_weather",
            version="1.0.0",
            description="Authenticated weather forecast service",
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            required_credentials=[self._api_key_ref] if self._secret_broker else [],
            rate_limits={"requests_per_minute": self._rpm, "burst_limit": 5},
            risk_ceiling=RiskLevel.READ,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [AuthenticatedMockWeatherTool(self, self._api_key_ref)]
