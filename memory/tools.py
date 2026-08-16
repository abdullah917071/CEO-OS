from __future__ import annotations

from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from memory.service import MemoryService, Provenance


class RememberMemoryTool:
    def __init__(self, service: MemoryService) -> None:
        self.service = service

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "memory.remember",
            "Store an owner-provided fact in permanent semantic memory",
            {
                "type": "object",
                "required": ["content"],
                "properties": {
                    "content": {"type": "string"},
                    "subject_key": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "importance": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
            RiskLevel.HARMLESS_WRITE,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        memory = await self.service.create(
            memory_type="semantic",
            content=str(arguments["content"]),
            subject_key=arguments.get("subject_key"),
            confidence=float(arguments.get("confidence", 1.0)),
            importance=float(arguments.get("importance", 0.7)),
            provenance=Provenance(source_type="owner_message"),
            dedupe_key=idempotency_key,
        )
        return ToolResult(memory.to_dict(), [f"Stored permanent memory {memory.id}"])


class SearchMemoryTool:
    def __init__(self, service: MemoryService) -> None:
        self.service = service

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "memory.search",
            "Search active permanent memories by semantic relevance",
            {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "memory_type": {"type": "string", "enum": ["semantic", "episodic"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            },
            RiskLevel.READ,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        matches = await self.service.search(
            str(arguments["query"]),
            memory_type=arguments.get("memory_type"),
            limit=int(arguments.get("limit", 5)),
        )
        evidence = [
            f"Memory {item.id} from {item.provenance[0].source_type}"
            for item in matches
            if item.provenance
        ]
        return ToolResult({"memories": [item.to_dict() for item in matches]}, evidence)


def memory_tools(service: MemoryService) -> list[RememberMemoryTool | SearchMemoryTool]:
    return [RememberMemoryTool(service), SearchMemoryTool(service)]
