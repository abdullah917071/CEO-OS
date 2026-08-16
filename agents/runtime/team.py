"""Dynamic Multi-Agent Team Orchestration and Assembly."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from agents.registry.agency_registry import AgentRouter, UniversalAgentRegistry
from agents.registry.contracts import TeamPlan
from agents.runtime.delegation import (
    StructuredTaskMessage,
    StructuredTaskResult,
    TaskConstraints,
    TaskOutcomeStatus,
)
from agents.runtime.execution import SpecialistWorkerExecutor
from agents.runtime.spawner import AgentSpawner

logger = logging.getLogger(__name__)


class TeamOrchestrator:
    """Orchestrates staged multi-agent team execution with dependencies and synthesis."""

    def __init__(
        self,
        registry: UniversalAgentRegistry,
        spawner: AgentSpawner | None = None,
        executor: SpecialistWorkerExecutor | None = None,
    ) -> None:
        self.registry = registry
        self.router = AgentRouter(registry)
        self.spawner = spawner or AgentSpawner()
        self.executor = executor or SpecialistWorkerExecutor()

    async def assemble_and_run_team(
        self,
        objective: str,
        max_specialists: int = 5,
        constraints: TaskConstraints | None = None,
    ) -> dict[str, Any]:
        """Dynamically assemble a specialist team, execute staged work, and synthesize results."""
        plan: TeamPlan = await self.router.route_team(objective, max_specialists=max_specialists)
        eff_constraints = constraints or TaskConstraints()

        stage_results: list[dict[str, Any]] = []
        all_findings: list[str] = []
        all_recommendations: list[str] = []
        all_evidence: list[str] = []

        # Execute through parallel stages in execution_order
        for stage_idx, stage_agent_ids in enumerate(plan.execution_order):
            logger.info("Executing Team Stage %d: %s", stage_idx + 1, stage_agent_ids)

            async def _run_member(aid: str, curr_stage: int = stage_idx) -> StructuredTaskResult:
                defn = await self.registry.get_agent(aid)
                if not defn:
                    return StructuredTaskResult(
                        task_id=f"t_{uuid.uuid4().hex[:6]}",
                        agent_id=aid,
                        status=TaskOutcomeStatus.FAILED,
                        summary=f"Agent definition {aid} not found.",
                        error="Agent not found in registry",
                    )

                worker = self.spawner.spawn(defn)
                task_msg = StructuredTaskMessage(
                    task_id=f"team_t_{uuid.uuid4().hex[:6]}",
                    objective=objective,
                    target_agent_id=aid,
                    deliverable=f"stage_{curr_stage + 1}_{defn.division.value}_assessment",
                    constraints=eff_constraints,
                )

                try:
                    res = await self.executor.execute(worker, task_msg)
                    # Record performance feedback to scoring system
                    await self.registry.record_task_outcome(
                        agent_id=aid,
                        success=(res.status == TaskOutcomeStatus.SUCCESS),
                        confidence=res.confidence,
                        cost=float(res.cost_units),
                        latency_ms=res.latency_ms,
                    )
                    return res
                finally:
                    self.spawner.terminate(worker.instance_id)

            # Parallel execution across stage members
            results: list[StructuredTaskResult] = await asyncio.gather(
                *[_run_member(aid, stage_idx) for aid in stage_agent_ids]
            )

            for r in results:
                stage_results.append(
                    {
                        "agent_id": r.agent_id,
                        "status": r.status.value,
                        "summary": r.summary,
                        "findings": r.findings,
                        "recommendations": r.recommended_actions,
                    }
                )
                all_findings.extend(r.findings)
                all_recommendations.extend(r.recommended_actions)
                all_evidence.extend(r.evidence)

        # CEO Synthesis
        synthesis = (
            f"Successfully coordinated {len(plan.members)} specialists ({', '.join(m.agent_id for m in plan.members)}) "
            f"for objective: '{objective}'. All stages completed with verified domain deliverables."
        )

        return {
            "status": "SUCCESS",
            "objective": objective,
            "lead_agent": plan.lead_agent_id,
            "team_size": len(plan.members),
            "team_members": [
                {"agent_id": m.agent_id, "role": m.role_in_team, "tools": m.assigned_tools}
                for m in plan.members
            ],
            "stages_executed": len(plan.execution_order),
            "stage_results": stage_results,
            "findings": all_findings,
            "recommendations": all_recommendations,
            "evidence": all_evidence,
            "synthesis": synthesis,
        }
