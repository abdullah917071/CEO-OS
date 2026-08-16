from __future__ import annotations

from core.contracts import CapabilitySpec, Tool, ToolResult


class CapabilityRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        name = tool.spec.name
        if name in self._tools:
            raise ValueError(f"Capability already registered: {name}")
        self._tools[name] = tool

    def unregister(self, name: str) -> bool:
        """Remove a capability by name. Returns True if removed, False if not found."""
        return self._tools.pop(name, None) is not None

    def unregister_by_source(self, source_prefix: str) -> list[str]:
        """Remove all capabilities matching a source prefix (e.g. 'mcp:server_name')."""
        removed: list[str] = []
        for name, tool in list(self._tools.items()):
            src = tool.spec.source
            if src == source_prefix or src.startswith(f"{source_prefix}:"):
                del self._tools[name]
                removed.append(name)
        return removed

    def get(self, name: str) -> Tool | None:
        """Look up a tool by capability name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check whether a capability is registered."""
        return name in self._tools

    def list(self) -> list[CapabilitySpec]:
        return sorted((tool.spec for tool in self._tools.values()), key=lambda item: item.name)

    async def execute(
        self, name: str, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        try:
            tool = self._tools[name]
        except KeyError as exc:
            raise ValueError(f"Unknown capability: {name}") from exc
        return await tool.execute(arguments, idempotency_key=idempotency_key)
