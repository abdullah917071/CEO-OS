from __future__ import annotations

from typing import Any

from computer.controller import ComputerController
from core.contracts import CapabilitySpec, RiskLevel, ToolResult


class ComputerTool:
    def __init__(
        self,
        controller: ComputerController,
        name: str,
        description: str,
        action: str,
        schema: dict[str, Any],
        risk: RiskLevel,
    ) -> None:
        self.controller = controller
        self.action = action
        self._spec = CapabilitySpec(name, description, schema, risk, source="macos-helper")

    @property
    def spec(self) -> CapabilitySpec:
        return self._spec

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        if self.action == "status":
            result = await self.controller.status()
        elif self.action == "stop":
            result = self.controller.stop()
        elif self.action == "list_apps":
            result = await self.controller.execute("list_apps")
        else:
            copied = dict(arguments)
            bundle_id = str(copied.pop("bundle_id"))
            result = await self.controller.execute(self.action, bundle_id=bundle_id, **copied)
        return ToolResult(result, [f"{self.spec.name} verified by macOS helper protocol V1"])


def computer_tools(
    controller: ComputerController, *, include_effects: bool = False
) -> list[ComputerTool]:
    bundle_schema = {
        "type": "object",
        "required": ["bundle_id"],
        "properties": {"bundle_id": {"type": "string"}},
    }
    read_tools = [
        ComputerTool(
            controller,
            "computer.status",
            "Inspect computer-control support and policy",
            "status",
            {},
            RiskLevel.READ,
        ),
        ComputerTool(
            controller,
            "computer.apps.list",
            "List installed and running macOS applications",
            "list_apps",
            {},
            RiskLevel.READ,
        ),
    ]
    if not include_effects:
        return read_tools
    return [
        *read_tools,
        ComputerTool(
            controller,
            "computer.app.open",
            "Open an allowlisted macOS application",
            "open_app",
            bundle_schema,
            RiskLevel.HARMLESS_WRITE,
        ),
        ComputerTool(
            controller,
            "computer.app.focus",
            "Focus an allowlisted running macOS application",
            "focus_app",
            bundle_schema,
            RiskLevel.HARMLESS_WRITE,
        ),
        ComputerTool(
            controller,
            "computer.text.type",
            "Type text into the verified frontmost application",
            "type_text",
            {
                "type": "object",
                "required": ["bundle_id", "text"],
                "properties": {
                    "bundle_id": {"type": "string"},
                    "text": {"type": "string", "maxLength": 10000},
                },
            },
            RiskLevel.HARMLESS_WRITE,
        ),
        ComputerTool(
            controller,
            "computer.key.press",
            "Press an allowlisted key in the verified frontmost application",
            "key_press",
            {
                "type": "object",
                "required": ["bundle_id", "key"],
                "properties": {
                    "bundle_id": {"type": "string"},
                    "key": {"type": "string"},
                    "modifiers": {"type": "array", "items": {"type": "string"}},
                },
            },
            RiskLevel.HARMLESS_WRITE,
        ),
        ComputerTool(
            controller,
            "computer.stop",
            "Stop computer effects and invalidate active ownership",
            "stop",
            {},
            RiskLevel.HARMLESS_WRITE,
        ),
    ]
