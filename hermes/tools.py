"""Capability tools for the Nous Hermes AI Agent subsystem."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from hermes.agent import HermesAIAgent


class HermesAgentRunTool(Tool):
    """Tool to execute an autonomous Hermes ReAct reasoning loop on an objective."""

    def __init__(self, agent: HermesAIAgent) -> None:
        self._agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="hermes.agent.run",
            description="Run autonomous Hermes multi-turn scratchpad reasoning and tool execution",
            input_schema={
                "type": "object",
                "required": ["task_id", "objective"],
                "properties": {
                    "task_id": {"type": "string", "description": "Unique task identifier"},
                    "objective": {"type": "string", "description": "Objective to accomplish"},
                    "max_turns": {
                        "type": "integer",
                        "default": 6,
                        "description": "Max reasoning turns",
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:hermes",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        task_id = str(arguments["task_id"])
        objective = str(arguments["objective"])
        max_turns = int(arguments.get("max_turns", 6))

        res = await self._agent.run(task_id=task_id, objective=objective, max_turns=max_turns)

        turns_count = len(res.trajectory.steps)
        evidence = [
            f"Hermes Agent executed in {res.duration_ms:.1f}ms with {turns_count} turns",
            f"Trajectory recorded: `{res.trajectory.trajectory_id}`",
        ]
        if res.evidence:
            evidence.extend(res.evidence)

        return ToolResult(
            output=dataclasses.asdict(res),
            evidence=evidence,
        )


class HermesReflectSynthesizeTool(Tool):
    """Tool to analyze a trajectory and synthesize a reusable skill."""

    def __init__(self, agent: HermesAIAgent) -> None:
        self._agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="hermes.reflect.synthesize",
            description="Perform post-task reflection and synthesize reusable SKILL.md blueprint",
            input_schema={
                "type": "object",
                "required": ["trajectory_id"],
                "properties": {
                    "trajectory_id": {
                        "type": "string",
                        "description": "ID of recorded trajectory",
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:hermes",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        trajectory_id = str(arguments["trajectory_id"])
        record = self._agent.trajectory_store.get(trajectory_id)
        if not record:
            return ToolResult(
                output={"error": f"Trajectory '{trajectory_id}' not found"},
                evidence=[f"Trajectory lookup failed for `{trajectory_id}`"],
            )

        reflection = self._agent.reflective_engine.reflect(record)
        insight_count = len(reflection.insights)
        lesson_count = len(reflection.lessons_learned)
        evidence = [f"Generated {insight_count} insights and {lesson_count} lessons"]
        if reflection.synthesized_skill:
            evidence.append(f"Synthesized skill: `{reflection.synthesized_skill.name}`")

        return ToolResult(
            output=dataclasses.asdict(reflection),
            evidence=evidence,
        )


class HermesTrajectoryExportTool(Tool):
    """Tool to export recorded trajectories to a JSONL dataset for fine-tuning."""

    def __init__(self, agent: HermesAIAgent) -> None:
        self._agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="hermes.trajectory.export",
            description="Export recorded trajectories to a JSONL dataset for Hermes fine-tuning",
            input_schema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Optional file path to write",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:hermes",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        output_path = arguments.get("output_path")
        jsonl_content = self._agent.trajectory_store.export_jsonl(output_path)
        count = self._agent.trajectory_store.count()

        evidence = [f"Exported {count} trajectories ({len(jsonl_content)} bytes)"]
        if output_path:
            evidence.append(f"Written to `{output_path}`")

        return ToolResult(
            output={"count": count, "jsonl_snippet": jsonl_content[:500]},
            evidence=evidence,
        )


class HermesSubagentSpawnTool(Tool):
    """Tool to spawn an isolated Hermes subagent for parallel delegation."""

    def __init__(self, agent: HermesAIAgent) -> None:
        self._agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="hermes.subagent.spawn",
            description="Spawn an isolated Hermes subagent with scoped capabilities and run a task",
            input_schema={
                "type": "object",
                "required": ["role", "objective"],
                "properties": {
                    "role": {"type": "string", "description": "Subagent specialized role"},
                    "objective": {"type": "string", "description": "Subagent objective"},
                    "allowed_capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Scoped capabilities for the subagent",
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:hermes",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        role = str(arguments["role"])
        objective = str(arguments["objective"])
        caps = arguments.get("allowed_capabilities", [])

        spec = self._agent.swarm.create_spec(
            role=role, objective=objective, allowed_capabilities=caps
        )
        result = await self._agent.swarm.spawn_and_execute(spec)

        return ToolResult(
            output=dataclasses.asdict(result),
            evidence=result.evidence,
        )
