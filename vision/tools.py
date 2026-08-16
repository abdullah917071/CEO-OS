from __future__ import annotations

from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from vision.runtime import VisionRuntime


class VisionTool:
    def __init__(
        self,
        runtime: VisionRuntime,
        name: str,
        description: str,
        action: str,
        schema: dict[str, Any],
        risk: RiskLevel,
    ) -> None:
        self.runtime = runtime
        self.action = action
        self._spec = CapabilitySpec(name, description, schema, risk, source="cua-driver")

    @property
    def spec(self) -> CapabilitySpec:
        return self._spec

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        if self.action == "status":
            output = await self.runtime.status()
        elif self.action == "windows":
            output = await self.runtime.list_windows(
                on_screen_only=bool(arguments.get("on_screen_only", True))
            )
        elif self.action == "capture":
            output = await self.runtime.capture(**arguments)
        else:
            output = await self.runtime.effect(
                self.action, arguments, idempotency_key=idempotency_key
            )
        return ToolResult(output, [f"{self.spec.name} enforced through Cua Driver adapter"])


def vision_tools(runtime: VisionRuntime, *, include_effects: bool = False) -> list[VisionTool]:
    target = {
        "session": {"type": "string", "maxLength": 64},
        "pid": {"type": "integer", "minimum": 1},
        "window_id": {"type": "integer", "minimum": 1},
        "delivery_mode": {
            "type": "string",
            "enum": ["background", "foreground"],
            "default": "background",
        },
        "expected_window_title": {"type": "string", "maxLength": 500},
    }
    target_schema = {
        "type": "object",
        "required": ["session", "pid", "window_id"],
        "properties": target,
    }
    safe = [
        VisionTool(
            runtime,
            "vision.status",
            "Inspect Cua Driver vision status",
            "status",
            {},
            RiskLevel.READ,
        ),
        VisionTool(
            runtime,
            "vision.windows.list",
            "List visible desktop windows without capturing their content",
            "windows",
            {
                "type": "object",
                "properties": {"on_screen_only": {"type": "boolean"}},
            },
            RiskLevel.READ,
        ),
        VisionTool(
            runtime,
            "vision.window.capture",
            "Capture bounded untrusted state for one exact listed window",
            "capture",
            target_schema,
            RiskLevel.READ,
        ),
    ]
    if not include_effects:
        return safe
    return [
        *safe,
        VisionTool(
            runtime,
            "vision.window.click",
            "Click one bounded point in an exact allowlisted window",
            "click",
            {
                "type": "object",
                "required": [*target_schema["required"], "x", "y"],
                "properties": {
                    **target,
                    "x": {"type": "number", "minimum": 0, "maximum": 16_384},
                    "y": {"type": "number", "minimum": 0, "maximum": 16_384},
                },
            },
            RiskLevel.EXTERNAL_COMMUNICATION,
        ),
        VisionTool(
            runtime,
            "vision.window.type",
            "Type bounded text into an exact allowlisted window",
            "type_text",
            {
                "type": "object",
                "required": [*target_schema["required"], "text"],
                "properties": {
                    **target,
                    "text": {"type": "string", "maxLength": 10_000},
                    "x": {"type": "number", "minimum": 0, "maximum": 16_384},
                    "y": {"type": "number", "minimum": 0, "maximum": 16_384},
                },
            },
            RiskLevel.EXTERNAL_COMMUNICATION,
        ),
        VisionTool(
            runtime,
            "vision.window.key",
            "Press an allowlisted key in an exact allowlisted window",
            "press_key",
            {
                "type": "object",
                "required": [*target_schema["required"], "key"],
                "properties": {
                    **target,
                    "key": {"type": "string"},
                    "modifiers": {"type": "array", "items": {"type": "string"}},
                },
            },
            RiskLevel.EXTERNAL_COMMUNICATION,
        ),
        VisionTool(
            runtime,
            "vision.window.scroll",
            "Scroll an exact allowlisted window",
            "scroll",
            {
                "type": "object",
                "required": [*target_schema["required"], "direction"],
                "properties": {
                    **target,
                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                    "amount": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            },
            RiskLevel.EXTERNAL_COMMUNICATION,
        ),
    ]
