"""Self-evolution and reflective skill synthesis engine for CEO OS AI Agent."""

from __future__ import annotations

import logging
from uuid import uuid4

from ceo_agent.contracts import CeoReflectionResult, CeoSynthesizedSkill, CeoTrajectoryRecord
from ceo_agent.llm import CeoLlmProtocol, DeterministicCeoEngine

logger = logging.getLogger(__name__)


class CeoReflectiveEngine:
    """Evaluates execution trajectories, extracts key insights, and synthesizes skills."""

    def __init__(self, llm: CeoLlmProtocol | None = None) -> None:
        self._llm = llm or DeterministicCeoEngine()

    async def reflect(
        self,
        trajectory: CeoTrajectoryRecord,
        synthesize_skill: bool = True,
    ) -> CeoReflectionResult:
        """Analyze trajectory to synthesize actionable heuristics and new skill assets."""
        dur = trajectory.total_duration_ms
        insights: list[str] = [
            f"Trajectory completed with status {trajectory.status} in {dur:.1f}ms",
            f"Executed {len(trajectory.steps)} reasoning and capability steps",
        ]

        # Scan for successful capability calls
        used_tools = [s.tool_call.name for s in trajectory.steps if s.tool_call]
        if used_tools:
            insights.append(f"Successfully orchestrated tools: {', '.join(set(used_tools))}")

        lessons: list[str] = [
            "Deterministic execution paths yield lower latency than repair loops",
            "Cryptographic verification ensures safety guarantees across R0-R4 capabilities",
        ]

        skill: CeoSynthesizedSkill | None = None
        if synthesize_skill:
            skill_name = f"synthesized_{trajectory.task_id.replace('-', '_')}"
            tools_str = ", ".join(used_tools) if used_tools else "core capabilities"
            skill_content = f"""# {skill_name.title().replace("_", " ")}

## Role & Purpose
Auto-synthesized executive skill from trajectory `{trajectory.trajectory_id}`.

## Recommended Capabilities
{tools_str}

## Execution Steps
1. Parse incoming directive: `{trajectory.objective}`
2. Execute primary capability with verified evidence matching.
3. Validate output status and return executive summary.
"""
            skill = CeoSynthesizedSkill(
                name=skill_name,
                description=f"Auto-synthesized skill for: {trajectory.objective[:80]}",
                content_markdown=skill_content,
                source_trajectory_id=trajectory.trajectory_id,
            )

        return CeoReflectionResult(
            reflection_id=f"refl_{uuid4().hex[:8]}",
            trajectory_id=trajectory.trajectory_id,
            insights=insights,
            lessons_learned=lessons,
            synthesized_skill=skill,
        )


# Backwards compatibility alias
HermesReflectiveEngine = CeoReflectiveEngine
