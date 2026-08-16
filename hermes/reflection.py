"""Hermes Reflective Engine: self-improvement, post-task reflection, and skill self-synthesis."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

from hermes.contracts import (
    HermesReflectionResult,
    HermesSynthesizedSkill,
    HermesTrajectoryRecord,
)


class HermesReflectiveEngine:
    """Evaluates task execution trajectories to generate reflections and skills."""

    def reflect(self, trajectory: HermesTrajectoryRecord) -> HermesReflectionResult:
        """Analyze a completed trajectory and extract lessons and skills."""
        insights: list[str] = []
        lessons: list[str] = []

        step_count = len(trajectory.steps)
        tools_called = [s.tool_call.name for s in trajectory.steps if s.tool_call]

        if trajectory.status == "SUCCESS":
            dur = trajectory.total_duration_ms
            insights.append(f"Accomplished objective in {step_count} step(s) ({dur:.1f}ms).")
            if tools_called:
                insights.append(f"Tool sequence: {' -> '.join(tools_called)}.")
                lessons.append(
                    f"For similar objectives, call tools in sequence: {', '.join(tools_called)}."
                )
            else:
                lessons.append("Executive synthesis succeeded without tool mutations.")
        else:
            insights.append(f"Concluded with status '{trajectory.status}'.")
            lessons.append("Verify prerequisites before mutations.")

        synthesized_skill: HermesSynthesizedSkill | None = None
        if tools_called:
            skill_slug = re.sub(r"[^\w]+", "-", trajectory.objective.lower()).strip("-")[:32]
            skill_name = f"hermes-auto-{skill_slug}"
            description = f"Synthesized workflow for: {trajectory.objective}"

            workflow_steps = "\n".join(
                f"{idx + 1}. **Call `{s.tool_call.name}`**: {s.thought}"
                for idx, s in enumerate(trajectory.steps)
                if s.tool_call
            )

            skill_md = f"""---
name: {skill_name}
description: {description}
---

# {trajectory.objective.title()}

Synthesized autonomous workflow from trajectory `{trajectory.trajectory_id}`.

## 🎯 Core Mission
- Execute `{trajectory.objective}` reliably with zero hallucination.

## 🚨 Critical Rules
- 1. Follow verified tool execution sequence: {", ".join(tools_called)}.
- 2. Collect and verify evidence after every capability invocation.

## 🔄 Verified Workflow Phases
{workflow_steps}
"""
            synthesized_skill = HermesSynthesizedSkill(
                name=skill_name,
                description=description,
                content_markdown=skill_md,
                source_trajectory_id=trajectory.trajectory_id,
            )

        return HermesReflectionResult(
            reflection_id=f"ref_{uuid4().hex[:8]}",
            trajectory_id=trajectory.trajectory_id,
            insights=insights,
            lessons_learned=lessons,
            synthesized_skill=synthesized_skill,
            evaluated_at=datetime.now(UTC).isoformat(),
        )
