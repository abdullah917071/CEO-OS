"""Universal Agent Registry and Router aggregating Native, Agency, Custom, and Generated providers."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from agents.registry.contracts import (
    AgentDefinition,
    AgentDivision,
    AgentProviderProtocol,
    AgentProviderSource,
    CandidateMatch,
    TeamMemberPlan,
    TeamPlan,
)
from agents.registry.providers import (
    AgencyAgentProvider,
    CustomAgentProvider,
    GeneratedAgentProvider,
    NativeAgentProvider,
)
from agents.registry.ranking import AgentRanker

logger = logging.getLogger(__name__)


class UniversalAgentRegistry:
    """Universal registry aggregating Native, Agency, Custom, and Generated agent providers."""

    def __init__(
        self,
        providers: Sequence[AgentProviderProtocol] | None = None,
    ) -> None:
        if providers:
            self.providers = list(providers)
        else:
            self.native_provider = NativeAgentProvider()
            self.agency_provider = AgencyAgentProvider()
            self.custom_provider = CustomAgentProvider()
            self.generated_provider = GeneratedAgentProvider()
            self.providers = [
                self.native_provider,
                self.agency_provider,
                self.custom_provider,
                self.generated_provider,
            ]
        self._ranker = AgentRanker()

    async def get_agent(self, agent_id: str) -> AgentDefinition | None:
        """Find an agent across all registered providers."""
        for p in self.providers:
            agent = await p.get_agent(agent_id)
            if agent:
                return agent
        return None

    async def list_all_agents(
        self,
        division: AgentDivision | None = None,
        source: AgentProviderSource | None = None,
    ) -> list[AgentDefinition]:
        """Aggregate all agents matching division or source filter."""
        results: list[AgentDefinition] = []
        seen_ids: set[str] = set()

        for p in self.providers:
            if source and p.source != source:
                continue
            agents = await p.list_agents()
            for a in agents:
                if a.id not in seen_ids:
                    if division is None or a.division == division:
                        seen_ids.add(a.id)
                        results.append(a)

        return sorted(results, key=lambda a: (not a.is_permanent, a.name))

    async def search(
        self,
        query: str,
        division: AgentDivision | None = None,
        limit: int = 10,
    ) -> list[CandidateMatch]:
        """Unified search across all providers with multi-factor ranking."""
        all_candidates: list[CandidateMatch] = []
        seen_ids: set[str] = set()

        for p in self.providers:
            matches = await p.search(query, division=division, limit=limit)
            for m in matches:
                if m.agent.id not in seen_ids:
                    seen_ids.add(m.agent.id)
                    all_candidates.append(m)

        # Apply global multi-factor ranking
        return self._ranker.rank(all_candidates, limit=limit)

    async def record_task_outcome(
        self,
        agent_id: str,
        success: bool,
        confidence: float = 0.90,
        cost: float = 1.0,
        latency_ms: float = 500.0,
        rating: float | None = None,
    ) -> None:
        """Update historical performance scoring for an agent persona."""
        agent = await self.get_agent(agent_id)
        if agent:
            agent.score.record_outcome(
                success=success,
                confidence=confidence,
                cost=cost,
                latency_ms=latency_ms,
                rating=rating,
            )
            logger.info(
                "Updated score for agent %s: success_rate=%.2f, tasks=%d",
                agent_id,
                agent.score.success_rate,
                agent.score.tasks_completed,
            )


class AgentRouter:
    """Intelligent router that matches directives to individual specialists or dynamic multi-agent teams."""

    def __init__(self, registry: UniversalAgentRegistry) -> None:
        self.registry = registry

    async def route_single(
        self,
        task: str,
        division: AgentDivision | None = None,
    ) -> CandidateMatch | None:
        """Find the single highest-scoring specialist for a directive."""
        matches = await self.registry.search(task, division=division, limit=3)
        return matches[0] if matches else None

    async def route_team(
        self,
        objective: str,
        max_specialists: int = 5,
    ) -> TeamPlan:
        """Dynamically assemble a coordinated team with role dependencies."""
        candidates = await self.registry.search(objective, limit=max_specialists + 2)

        if not candidates:
            # Fallback to CEO as sole lead
            ceo_agent = await self.registry.get_agent("ceo")
            return TeamPlan(
                objective=objective,
                lead_agent_id="ceo",
                members=[
                    TeamMemberPlan(
                        agent_id="ceo",
                        role_in_team="lead",
                        assigned_subtasks=[objective],
                        assigned_tools=list(ceo_agent.default_tools) if ceo_agent else [],
                    )
                ],
                execution_order=[["ceo"]],
            )

        lead = candidates[0].agent
        members: list[TeamMemberPlan] = []
        lead_id = lead.id

        # Lead role
        members.append(
            TeamMemberPlan(
                agent_id=lead_id,
                role_in_team="lead",
                assigned_subtasks=[f"Plan and supervise: {objective}"],
                assigned_tools=list(lead.default_tools),
            )
        )

        # Specialist members
        specialist_ids: list[str] = []
        for match in candidates[1:max_specialists]:
            sp = match.agent
            members.append(
                TeamMemberPlan(
                    agent_id=sp.id,
                    role_in_team="specialist",
                    assigned_subtasks=[f"Execute {sp.role} tasks for: {objective}"],
                    depends_on_agents=[lead_id],
                    assigned_tools=list(sp.default_tools),
                )
            )
            specialist_ids.append(sp.id)

        # Execution order: Stage 1 = Lead plans, Stage 2 = Specialists in parallel, Stage 3 = Lead synthesizes
        execution_order = [[lead_id]]
        if specialist_ids:
            execution_order.append(specialist_ids)
            execution_order.append([lead_id])

        return TeamPlan(
            objective=objective,
            lead_agent_id=lead_id,
            members=members,
            execution_order=execution_order,
            estimated_cost=float(len(members) * 1.5),
        )
