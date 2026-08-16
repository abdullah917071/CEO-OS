"""Integration registry: manages lifecycle and tool collection for all providers."""

from __future__ import annotations

import logging
from collections.abc import Callable

from core.contracts import Tool
from integrations.contracts import (
    IntegrationHealth,
    IntegrationProvider,
    IntegrationStatus,
)
from integrations.mcp_adapter import MCP_AVAILABLE, McpServerConfig, McpServerProvider
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)

# Callback signature for tool change notifications: (registry) -> None
ToolChangeListener = Callable[["IntegrationRegistry"], None]


class IntegrationRegistry:
    """Holds registered integration providers and manages their lifecycle."""

    def __init__(self) -> None:
        self._providers: dict[str, IntegrationProvider] = {}
        self._listeners: list[ToolChangeListener] = []

    def add_listener(self, listener: ToolChangeListener) -> None:
        """Register a callback for when tools or integrations change."""
        self._listeners.append(listener)

    def _notify_listeners(self) -> None:
        """Notify all listeners that integration tools have changed."""
        for listener in self._listeners:
            try:
                listener(self)
            except Exception:
                logger.warning("Error in integration registry listener", exc_info=True)

    def register(self, provider: IntegrationProvider) -> None:
        """Register a provider. Raises on duplicate name."""
        status = provider.status()
        name = status.name
        if name in self._providers:
            raise ValueError(f"Integration already registered: {name}")
        self._providers[name] = provider

    async def install_mcp(
        self,
        config: McpServerConfig,
        secret_broker: SecretBroker | None = None,
    ) -> IntegrationStatus:
        """Dynamically install, register, and connect an MCP server."""
        if not MCP_AVAILABLE:
            raise RuntimeError("The 'mcp' package is not installed")
        if config.name in self._providers:
            raise ValueError(f"Integration already registered: {config.name}")

        provider = McpServerProvider(config, secret_broker=secret_broker)
        self.register(provider)
        await provider.connect()
        self._notify_listeners()
        return provider.status()

    async def install_native(
        self,
        provider: NativeIntegrationProvider,
    ) -> IntegrationStatus:
        """Dynamically install, register, and connect a native integration."""
        status = provider.status()
        if status.name in self._providers:
            raise ValueError(f"Integration already registered: {status.name}")

        self.register(provider)
        await provider.connect()
        self._notify_listeners()
        return provider.status()

    async def uninstall(self, name: str) -> bool:
        """Remove and disconnect a provider by name."""
        provider = self._providers.pop(name, None)
        if provider is None:
            return False
        try:
            await provider.disconnect()
        except Exception:
            logger.warning(
                "Error disconnecting integration %s during uninstall", name, exc_info=True
            )
        self._notify_listeners()
        return True

    async def unregister(self, name: str) -> None:
        """Remove and disconnect a provider by name."""
        await self.uninstall(name)

    def list_integrations(self) -> list[IntegrationStatus]:
        """Return status snapshots for all registered providers."""
        return sorted(
            (provider.status() for provider in self._providers.values()),
            key=lambda s: s.name,
        )

    def get(self, name: str) -> IntegrationProvider | None:
        """Look up a provider by name."""
        return self._providers.get(name)

    def all_tools(self) -> list[Tool]:
        """Collect tools from all connected, healthy providers."""
        result: list[Tool] = []
        for provider in self._providers.values():
            status = provider.status()
            if status.health in {IntegrationHealth.HEALTHY, IntegrationHealth.DEGRADED}:
                result.extend(provider.tools())
        return result

    async def connect_all(self) -> None:
        """Connect every registered provider. Failures are logged, not raised."""
        for name, provider in self._providers.items():
            try:
                await provider.connect()
                logger.info("Integration connected: %s", name)
            except Exception:
                logger.error("Failed to connect integration %s", name, exc_info=True)
        self._notify_listeners()

    async def disconnect_all(self) -> None:
        """Disconnect every registered provider."""
        for name, provider in self._providers.items():
            try:
                await provider.disconnect()
            except Exception:
                logger.warning("Error disconnecting integration %s", name, exc_info=True)
        self._notify_listeners()
