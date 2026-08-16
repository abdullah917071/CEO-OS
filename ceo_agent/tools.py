"""Capability tools for the CEO OS ReAct Reasoning Engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ceo_agent.agent import CeoAIAgent
from ceo_agent.contracts import CeoSubagentSpec
from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult


class CeoAgentRunTool(Tool):
    """Tool allowing autonomous ReAct reasoning loop execution."""

    def __init__(self, agent: CeoAIAgent) -> None:
        self.agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="ceo.agent.run",
            description="Run autonomous multi-turn ReAct reasoning loop for a complex objective",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Unique task identifier"},
                    "objective": {"type": "string", "description": "Objective to accomplish"},
                    "max_turns": {"type": "integer", "default": 6, "description": "Max turns"},
                },
                "required": ["task_id", "objective"],
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:ceo-agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        task_id = str(arguments["task_id"])
        objective = str(arguments["objective"])
        max_turns = int(arguments.get("max_turns", 6))

        res = await self.agent.run(task_id=task_id, objective=objective, max_turns=max_turns)
        return ToolResult(
            output={
                "run_id": res.run_id,
                "task_id": res.task_id,
                "status": res.status,
                "thought": res.thought,
                "final_answer": res.final_answer,
                "duration_ms": res.duration_ms,
                "steps_count": len(res.trajectory.steps),
            },
            evidence=res.evidence
            or [f"Completed CEO OS autonomous reasoning loop: status={res.status}"],
        )


class CeoReflectSynthesizeTool(Tool):
    """Tool allowing post-task reflection and self-evolution skill synthesis."""

    def __init__(self, agent: CeoAIAgent) -> None:
        self.agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="ceo.agent.reflect",
            description="Reflect on trajectory to synthesize actionable heuristics and new skills",
            input_schema={
                "type": "object",
                "properties": {
                    "trajectory_id": {"type": "string", "description": "ID of trajectory"},
                    "synthesize_skill": {"type": "boolean", "default": True},
                },
                "required": ["trajectory_id"],
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:ceo-agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        traj_id = str(arguments["trajectory_id"])
        synthesize_skill = bool(arguments.get("synthesize_skill", True))

        record = self.agent.trajectory_store.get(traj_id)
        if not record:
            return ToolResult(
                output={"error": f"Trajectory not found: {traj_id}"},
                evidence=[f"Failed reflection: trajectory `{traj_id}` not found"],
            )

        reflection = await self.agent.reflective_engine.reflect(
            record, synthesize_skill=synthesize_skill
        )
        skill_name = reflection.synthesized_skill.name if reflection.synthesized_skill else "None"
        return ToolResult(
            output={
                "reflection_id": reflection.reflection_id,
                "trajectory_id": reflection.trajectory_id,
                "insights": reflection.insights,
                "lessons_learned": reflection.lessons_learned,
                "synthesized_skill": (
                    {
                        "name": reflection.synthesized_skill.name,
                        "description": reflection.synthesized_skill.description,
                        "content_markdown": reflection.synthesized_skill.content_markdown,
                    }
                    if reflection.synthesized_skill
                    else None
                ),
            },
            evidence=[
                f"Generated {len(reflection.insights)} insights and synthesized skill: {skill_name}"
            ],
        )


class CeoSubagentSpawnTool(Tool):
    """Tool to spawn parallelized worker subagents."""

    def __init__(self, agent: CeoAIAgent) -> None:
        self.agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="ceo.agent.spawn",
            description="Spawn a focused subagent with bounded capability budget",
            input_schema={
                "type": "object",
                "properties": {
                    "subagent_id": {"type": "string"},
                    "role": {"type": "string"},
                    "objective": {"type": "string"},
                    "allowed_capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "max_turns": {"type": "integer", "default": 5},
                },
                "required": ["subagent_id", "role", "objective"],
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:ceo-agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        spec = CeoSubagentSpec(
            subagent_id=str(arguments["subagent_id"]),
            role=str(arguments["role"]),
            objective=str(arguments["objective"]),
            allowed_capabilities=list(arguments.get("allowed_capabilities", [])),
            max_turns=int(arguments.get("max_turns", 5)),
        )
        res = await self.agent.swarm.spawn(spec)
        return ToolResult(
            output={
                "subagent_id": res.subagent_id,
                "objective": res.objective,
                "status": res.status,
                "output": res.output,
                "duration_ms": res.duration_ms,
            },
            evidence=res.evidence or [f"Subagent `{res.subagent_id}` finished with {res.status}"],
        )


class CeoTrajectoryExportTool(Tool):
    """Tool to export trajectory datasets in JSONL format."""

    def __init__(self, agent: CeoAIAgent) -> None:
        self.agent = agent

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="ceo.agent.trajectories.export",
            description="Export all recorded reasoning trajectories into JSONL dataset format",
            input_schema={
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "default": "./data/trajectories.jsonl"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:ceo-agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        out_path = Path(str(arguments.get("output_path", "./data/trajectories.jsonl")))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        count = self.agent.trajectory_store.export_jsonl(out_path)
        return ToolResult(
            output={"exported_count": count, "file_path": str(out_path)},
            evidence=[f"Exported {count} trajectories to `{out_path}`"],
        )


# Backwards compatibility aliases
HermesAgentRunTool = CeoAgentRunTool
HermesReflectSynthesizeTool = CeoReflectSynthesizeTool
HermesSubagentSpawnTool = CeoSubagentSpawnTool
HermesTrajectoryExportTool = CeoTrajectoryExportTool
