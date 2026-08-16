from __future__ import annotations

from agents.runtime import AgentRuntime
from core.contracts import CapabilitySpec, RiskLevel, ToolResult


class DelegateResearchTool:
    def __init__(self, runtime: AgentRuntime) -> None:
        self.runtime = runtime

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agents.delegate.research",
            "Run a bounded, parallel research simulation through temporary workers",
            {
                "type": "object",
                "required": ["objective", "items"],
                "properties": {
                    "objective": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}, "maxItems": 100},
                    "worker_count": {"type": "integer", "minimum": 1, "maximum": 10},
                },
            },
            RiskLevel.READ,
            source="agent_runtime",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        objective = arguments.get("objective")
        items = arguments.get("items")
        worker_count = arguments.get("worker_count", 4)
        if (
            not isinstance(objective, str)
            or not isinstance(items, list)
            or not all(isinstance(item, str) for item in items)
            or not isinstance(worker_count, int)
        ):
            raise ValueError("objective, string items, and integer worker_count are required")
        result = await self.runtime.delegate(objective, items, worker_count=worker_count)
        return ToolResult(result, list(result["evidence"]))


def agent_tools(runtime: AgentRuntime) -> list[DelegateResearchTool]:
    return [DelegateResearchTool(runtime)]
