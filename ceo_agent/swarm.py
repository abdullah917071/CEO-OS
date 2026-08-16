"""Subagent swarm delegator for parallelized CEO OS multi-agent reasoning."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from ceo_agent.contracts import CeoSubagentResult, CeoSubagentSpec

if TYPE_CHECKING:
    from ceo_agent.agent import CeoAIAgent


class CeoSubagentSwarm:
    """Manages parallelized worker subagents operating under bounded budgets."""

    def __init__(self, parent_agent: CeoAIAgent) -> None:
        self.parent_agent = parent_agent

    async def spawn(self, spec: CeoSubagentSpec) -> CeoSubagentResult:
        """Spawn a child subagent to execute a focused sub-objective."""
        start_time = time.perf_counter()
        from ceo_agent.agent import CeoAIAgent

        child = CeoAIAgent(
            llm=self.parent_agent.llm,
            prompt_formatter=self.parent_agent.prompt_formatter,
            capabilities=self.parent_agent.capabilities,
            trajectory_store=self.parent_agent.trajectory_store,
        )

        res = await child.run(
            task_id=spec.subagent_id,
            objective=f"[{spec.role}] {spec.objective}",
            max_turns=spec.max_turns,
        )

        duration = (time.perf_counter() - start_time) * 1000.0
        return CeoSubagentResult(
            subagent_id=spec.subagent_id,
            objective=spec.objective,
            status=res.status,
            output=res.final_answer,
            evidence=res.evidence,
            duration_ms=duration,
        )

    async def spawn_parallel(self, specs: list[CeoSubagentSpec]) -> list[CeoSubagentResult]:
        """Execute multiple subagent specs concurrently."""
        tasks = [self.spawn(s) for s in specs]
        return await asyncio.gather(*tasks)


# Backwards compatibility alias
HermesSubagentSwarm = CeoSubagentSwarm
