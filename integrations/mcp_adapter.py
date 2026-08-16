"""MCP client adapter: connects to MCP stdio servers and adapts their tools for CEO OS."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from integrations.contracts import (
    IntegrationHealth,
    IntegrationManifest,
    IntegrationStatus,
    IntegrationType,
)
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)

try:
    from mcp import Client, StdioServerParameters  # type: ignore[import-untyped]
    from mcp.client.stdio import stdio_client  # type: ignore[import-untyped]

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


# ── Risk mapping ────────────────────────────────────────────────────────────
# MCP tools do not carry CEO risk classes, so we assign them from the server
# config risk_ceiling. The server admin decides the maximum damage class.

_RISK_ORDER: list[RiskLevel] = [
    RiskLevel.READ,
    RiskLevel.HARMLESS_WRITE,
    RiskLevel.EXTERNAL_COMMUNICATION,
    RiskLevel.BUSINESS_CHANGE,
    RiskLevel.DESTRUCTIVE_ADMIN,
]


def _cap_risk(requested: RiskLevel, ceiling: RiskLevel) -> RiskLevel:
    """Return the lower of *requested* and *ceiling*."""
    if _RISK_ORDER.index(requested) <= _RISK_ORDER.index(ceiling):
        return requested
    return ceiling


# ── Configuration ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class McpServerConfig:
    """Declarative configuration for one MCP stdio server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    domain: str = "integrations"
    risk_ceiling: RiskLevel = RiskLevel.HARMLESS_WRITE
    enabled: bool = True
    timeout_seconds: int = 30


# ── Tool adapter ────────────────────────────────────────────────────────────


class McpToolAdapter:
    """Wraps a single MCP tool definition as a CEO OS Tool."""

    def __init__(
        self,
        tool_name: str,
        tool_description: str,
        tool_input_schema: dict[str, Any],
        server_name: str,
        risk_ceiling: RiskLevel,
        client: Any,
        timeout_seconds: int,
    ) -> None:
        self._name = tool_name
        self._description = tool_description
        self._input_schema = tool_input_schema
        self._server_name = server_name
        self._risk = _cap_risk(RiskLevel.HARMLESS_WRITE, risk_ceiling)
        self._client = client
        self._timeout = timeout_seconds

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name=self._name,
            description=self._description,
            input_schema=self._input_schema,
            risk=self._risk,
            source=f"mcp:{self._server_name}",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key  # MCP has no idempotency; hint only.
        result = await asyncio.wait_for(
            self._client.call_tool(self._name, arguments),
            timeout=self._timeout,
        )
        if result.is_error:
            # Extract text from error content blocks.
            parts: list[str] = []
            for block in result.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
            raise RuntimeError(f"MCP tool {self._name} error: {' '.join(parts) or 'unknown'}")
        # Extract text content into output dict.
        texts: list[str] = []
        for block in result.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        output_text = "\n".join(texts)
        # Try to parse as JSON for structured output.
        try:
            output = json.loads(output_text)
            if not isinstance(output, dict):
                output = {"result": output}
        except (json.JSONDecodeError, ValueError):
            output = {"result": output_text}
        return ToolResult(output, [f"MCP tool {self._name} executed via {self._server_name}"])


# ── Server provider ─────────────────────────────────────────────────────────


class McpServerProvider:
    """Manages an MCP stdio server subprocess and adapts its tools."""

    def __init__(
        self,
        config: McpServerConfig,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        if not MCP_AVAILABLE:
            raise RuntimeError("The 'mcp' package is not installed")
        self._config = config
        self._secret_broker = secret_broker
        self._client: Any | None = None
        self._context: Any | None = None
        self._tools: list[McpToolAdapter] = []
        self._health = IntegrationHealth.UNKNOWN
        self._connected_at: datetime | None = None
        self._error: str | None = None

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name=self._config.name,
            version="mcp-stdio",
            description=f"MCP server: {self._config.command} {' '.join(self._config.args)}",
            integration_type=IntegrationType.MCP,
            domain=self._config.domain,
            capabilities=[t.spec for t in self._tools],
            risk_ceiling=self._config.risk_ceiling,
            enabled=self._config.enabled,
        )

    def _resolve_env(self) -> dict[str, str] | None:
        """Resolve secret references in environment variables via SecretBroker."""
        if not self._config.env:
            return None
        resolved: dict[str, str] = {}
        for key, val in self._config.env.items():
            if str(val).startswith("cred_") and self._secret_broker:
                lease = self._secret_broker.lease_secret(str(val), f"mcp:{self._config.name}")
                resolved[key] = lease.secret_value
            else:
                resolved[key] = str(val)
        return resolved

    async def connect(self) -> None:
        """Start the MCP server subprocess and discover its tools."""
        try:
            resolved_env = self._resolve_env()
            params = StdioServerParameters(
                command=self._config.command,
                args=self._config.args,
                env=resolved_env,
            )
            self._context = stdio_client(params)
            read_write = await self._context.__aenter__()
            self._client = Client(read_write)
            await self._client.__aenter__()
            tool_list = await self._client.list_tools()
            self._tools = [
                McpToolAdapter(
                    tool_name=tool.name,
                    tool_description=tool.description or "",
                    tool_input_schema=tool.input_schema or {},
                    server_name=self._config.name,
                    risk_ceiling=self._config.risk_ceiling,
                    client=self._client,
                    timeout_seconds=self._config.timeout_seconds,
                )
                for tool in tool_list.tools
            ]
            self._health = IntegrationHealth.HEALTHY
            self._connected_at = datetime.now(UTC)
            self._error = None
            logger.info(
                "MCP server %s connected with %d tools",
                self._config.name,
                len(self._tools),
            )
        except Exception as exc:
            self._health = IntegrationHealth.UNAVAILABLE
            self._error = str(exc)
            logger.error("MCP server %s failed to connect: %s", self._config.name, exc)

    async def disconnect(self) -> None:
        """Shut down the MCP server subprocess."""
        try:
            if self._client is not None:
                await self._client.__aexit__(None, None, None)
                self._client = None
            if self._context is not None:
                await self._context.__aexit__(None, None, None)
                self._context = None
        except Exception:
            logger.warning("Error disconnecting MCP server %s", self._config.name, exc_info=True)
        finally:
            self._tools = []
            self._health = IntegrationHealth.UNAVAILABLE
            self._connected_at = None

    def status(self) -> IntegrationStatus:
        return IntegrationStatus(
            name=self._config.name,
            version="mcp-stdio",
            description=f"MCP server: {self._config.command} {' '.join(self._config.args)}",
            integration_type=IntegrationType.MCP,
            health=self._health,
            tool_count=len(self._tools),
            risk_ceiling=self._config.risk_ceiling,
            enabled=self._config.enabled,
            domain=self._config.domain,
            connected_at=self._connected_at,
            error=self._error,
        )

    def tools(self) -> list[Tool]:
        return list(self._tools)
