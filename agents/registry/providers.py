"""Provider implementations for Native, Agency, Custom, and Generated agent sources."""

from __future__ import annotations

import logging

from agents.registry.contracts import (
    AgentDefinition,
    AgentDivision,
    AgentProviderProtocol,
    AgentProviderSource,
    AgentScore,
    CandidateMatch,
)
from agents.registry.loader import AgentLoader
from agents.registry.ranking import AgentRanker
from agents.registry.search import AgentSearchEngine

logger = logging.getLogger(__name__)


# ── 1. Native Permanent Director Agents ─────────────────────────────────────────


def _build_native_directors() -> list[AgentDefinition]:
    """Define the 7 permanent executive directors of CEO OS."""
    return [
        AgentDefinition(
            id="ceo",
            name="CEO",
            division=AgentDivision.GENERAL,
            role="Chief Executive Officer",
            description="Autonomous Executive orchestrator and decision maker for CEO OS.",
            instructions="You are the CEO. You evaluate tasks, search the specialist roster, assemble teams, and synthesize outcomes.",
            source=AgentProviderSource.NATIVE,
            tags=["ceo", "executive", "orchestrator", "leader"],
            default_tools=[
                "agents.search",
                "agents.spawn",
                "agents.delegate",
                "memory.recall",
                "memory.remember",
            ],
            allowed_capabilities=[
                "agents.search",
                "agents.spawn",
                "agents.delegate",
                "memory.recall",
                "memory.remember",
            ],
            model_class="high_reasoning",
            is_permanent=True,
            score=AgentScore(tasks_completed=100, success_rate=0.99, owner_rating=5.0),
        ),
        AgentDefinition(
            id="marketing-director",
            name="Marketing Director",
            division=AgentDivision.MARKETING,
            role="Marketing Director",
            description="Leads growth, performance ads, brand strategy, attribution, and multi-channel campaigns.",
            instructions="You are the Marketing Director. Lead marketing campaigns, delegate to paid media, SEO, copy, and CRO specialists.",
            source=AgentProviderSource.NATIVE,
            tags=["marketing", "growth", "ads", "seo", "director"],
            default_tools=[
                "meta.ads.create",
                "marketing.snapshot.get",
                "browser.read",
                "comms.email.send",
                "memory.recall",
            ],
            allowed_capabilities=[
                "meta.ads.create",
                "marketing.snapshot.get",
                "browser.read",
                "comms.email.send",
                "memory.recall",
            ],
            model_class="medium_reasoning",
            is_permanent=True,
            score=AgentScore(tasks_completed=50, success_rate=0.95, owner_rating=4.9),
        ),
        AgentDefinition(
            id="finance-director",
            name="Finance Director",
            division=AgentDivision.FINANCE,
            role="Finance Director / CFO",
            description="Leads financial modeling, cost optimization, invoicing, unit economics, and FP&A.",
            instructions="You are the Finance Director. Oversee cash flow, audit spend, manage invoices, and forecast budgets.",
            source=AgentProviderSource.NATIVE,
            tags=["finance", "cfo", "budget", "cost", "invoices", "director"],
            default_tools=[
                "business.finance.overview",
                "business.finance.invoices",
                "production.cost.overview",
                "memory.recall",
            ],
            allowed_capabilities=[
                "business.finance.overview",
                "business.finance.invoices",
                "production.cost.overview",
                "memory.recall",
            ],
            model_class="medium_reasoning",
            is_permanent=True,
            score=AgentScore(tasks_completed=40, success_rate=0.97, owner_rating=4.9),
        ),
        AgentDefinition(
            id="operations-director",
            name="Operations Director",
            division=AgentDivision.OPERATIONS,
            role="Operations Director / COO",
            description="Manages workflow delivery, operational SLA, capacity, and sprint orchestration.",
            instructions="You are the Operations Director. Ensure smooth cross-functional execution and workflow integrity.",
            source=AgentProviderSource.NATIVE,
            tags=["operations", "coo", "workflow", "sprint", "director"],
            default_tools=["tasks.list", "agents.spawn", "memory.recall", "memory.remember"],
            allowed_capabilities=["tasks.list", "agents.spawn", "memory.recall", "memory.remember"],
            model_class="medium_reasoning",
            is_permanent=True,
            score=AgentScore(tasks_completed=60, success_rate=0.96, owner_rating=4.8),
        ),
        AgentDefinition(
            id="developer-director",
            name="Developer Director",
            division=AgentDivision.ENGINEERING,
            role="Developer Director / VP Engineering",
            description="Leads architecture, software engineering, automated QA, security, and releases.",
            instructions="You are the Developer Director. Oversee technical architecture, delegate to coding, backend, and QA specialists.",
            source=AgentProviderSource.NATIVE,
            tags=["engineering", "developer", "architecture", "cto", "director"],
            default_tools=[
                "files.read",
                "files.write",
                "tools.shell",
                "memory.recall",
                "memory.remember",
            ],
            allowed_capabilities=[
                "files.read",
                "files.write",
                "tools.shell",
                "memory.recall",
                "memory.remember",
            ],
            model_class="coding",
            is_permanent=True,
            score=AgentScore(tasks_completed=80, success_rate=0.98, owner_rating=5.0),
        ),
        AgentDefinition(
            id="research-director",
            name="Research Director",
            division=AgentDivision.RESEARCH,
            role="Research Director",
            description="Leads market research, competitor intelligence, data analytics, and deep analysis.",
            instructions="You are the Research Director. Coordinate research workers to gather intelligence and validate assumptions.",
            source=AgentProviderSource.NATIVE,
            tags=["research", "analysis", "intelligence", "data", "director"],
            default_tools=[
                "web.search",
                "browser.read",
                "data.read",
                "memory.recall",
                "memory.remember",
            ],
            allowed_capabilities=[
                "web.search",
                "browser.read",
                "data.read",
                "memory.recall",
                "memory.remember",
            ],
            model_class="medium_reasoning",
            is_permanent=True,
            score=AgentScore(tasks_completed=45, success_rate=0.94, owner_rating=4.8),
        ),
        AgentDefinition(
            id="communications-director",
            name="Communications Director",
            division=AgentDivision.COMMUNICATIONS,
            role="Communications Director",
            description="Leads internal/external communications, customer relations, PR, and technical documentation.",
            instructions="You are the Communications Director. Supervise customer support, messaging, emails, and publications.",
            source=AgentProviderSource.NATIVE,
            tags=["communications", "comms", "pr", "support", "director"],
            default_tools=["comms.email.send", "files.read", "files.write", "memory.recall"],
            allowed_capabilities=["comms.email.send", "files.read", "files.write", "memory.recall"],
            model_class="medium_reasoning",
            is_permanent=True,
            score=AgentScore(tasks_completed=35, success_rate=0.96, owner_rating=4.9),
        ),
    ]


class NativeAgentProvider(AgentProviderProtocol):
    """Provides the permanent executive directors of CEO OS."""

    def __init__(self) -> None:
        self._agents = {a.id: a for a in _build_native_directors()}

    @property
    def source(self) -> AgentProviderSource:
        return AgentProviderSource.NATIVE

    async def list_agents(self) -> list[AgentDefinition]:
        return list(self._agents.values())

    async def get_agent(self, agent_id: str) -> AgentDefinition | None:
        clean = agent_id.strip().lower()
        return self._agents.get(clean)

    async def search(
        self, query: str, division: AgentDivision | None = None, limit: int = 10
    ) -> list[CandidateMatch]:
        engine = AgentSearchEngine(list(self._agents.values()))
        candidates = engine.search(query, division=division, limit=limit)
        return AgentRanker().rank(candidates, limit=limit)


# ── 2. Agency Agents Provider (270+ Specialist Personas) ───────────────────────


class AgencyAgentProvider(AgentProviderProtocol):
    """Provides the 270+ specialist agent personas from Agency Agents catalog."""

    def __init__(self, loader: AgentLoader | None = None) -> None:
        self.loader = loader or AgentLoader()
        self._search_engine: AgentSearchEngine | None = None
        self._ranker = AgentRanker()

    @property
    def source(self) -> AgentProviderSource:
        return AgentProviderSource.AGENCY

    def _ensure_search_engine(self) -> AgentSearchEngine:
        if self._search_engine is None:
            all_agents = list(self.loader.load_all().values())
            self._search_engine = AgentSearchEngine(all_agents)
        return self._search_engine

    async def list_agents(self) -> list[AgentDefinition]:
        return list(self.loader.load_all().values())

    async def get_agent(self, agent_id: str) -> AgentDefinition | None:
        return self.loader.get(agent_id)

    async def search(
        self, query: str, division: AgentDivision | None = None, limit: int = 10
    ) -> list[CandidateMatch]:
        engine = self._ensure_search_engine()
        candidates = engine.search(query, division=division, limit=limit * 2)
        return self._ranker.rank(candidates, limit=limit)


# ── 3. Custom Agent Provider ───────────────────────────────────────────────────


class CustomAgentProvider(AgentProviderProtocol):
    """Provides user-created or workspace-specific custom agent definitions."""

    def __init__(self) -> None:
        self._custom_agents: dict[str, AgentDefinition] = {}
        self._ranker = AgentRanker()

    @property
    def source(self) -> AgentProviderSource:
        return AgentProviderSource.CUSTOM

    def register_custom_agent(self, agent: AgentDefinition) -> None:
        agent.source = AgentProviderSource.CUSTOM
        self._custom_agents[agent.id] = agent

    async def list_agents(self) -> list[AgentDefinition]:
        return list(self._custom_agents.values())

    async def get_agent(self, agent_id: str) -> AgentDefinition | None:
        return self._custom_agents.get(agent_id.strip().lower())

    async def search(
        self, query: str, division: AgentDivision | None = None, limit: int = 10
    ) -> list[CandidateMatch]:
        if not self._custom_agents:
            return []
        engine = AgentSearchEngine(list(self._custom_agents.values()))
        candidates = engine.search(query, division=division, limit=limit)
        return self._ranker.rank(candidates, limit=limit)


# ── 4. Generated Agent Provider (Dynamic On-Demand Specialists) ────────────────


class GeneratedAgentProvider(AgentProviderProtocol):
    """Provides on-the-fly dynamically created specialist agents generated when no match exists."""

    def __init__(self) -> None:
        self._generated_agents: dict[str, AgentDefinition] = {}
        self._ranker = AgentRanker()

    @property
    def source(self) -> AgentProviderSource:
        return AgentProviderSource.GENERATED

    def create_dynamic_agent(
        self,
        name: str,
        role: str,
        division: AgentDivision,
        mission: str,
        tools: list[str] | None = None,
    ) -> AgentDefinition:
        """Create a new temporary specialist agent on demand."""
        clean_id = f"generated-{name.lower().replace(' ', '-')}"
        agent = AgentDefinition(
            id=clean_id,
            name=name,
            division=division,
            role=role,
            description=f"Dynamically generated specialist: {role}",
            instructions=f"You are a specialist in {role}. Mission: {mission}",
            source=AgentProviderSource.GENERATED,
            tags=["generated", division.value, clean_id],
            default_tools=tools or ["memory.recall", "memory.remember"],
            allowed_capabilities=tools or ["memory.recall", "memory.remember"],
            model_class="medium_reasoning",
            is_permanent=False,
            score=AgentScore(tasks_completed=0, success_rate=1.0),
        )
        self._generated_agents[clean_id] = agent
        return agent

    async def list_agents(self) -> list[AgentDefinition]:
        return list(self._generated_agents.values())

    async def get_agent(self, agent_id: str) -> AgentDefinition | None:
        return self._generated_agents.get(agent_id.strip().lower())

    async def search(
        self, query: str, division: AgentDivision | None = None, limit: int = 10
    ) -> list[CandidateMatch]:
        if not self._generated_agents:
            return []
        engine = AgentSearchEngine(list(self._generated_agents.values()))
        candidates = engine.search(query, division=division, limit=limit)
        return self._ranker.rank(candidates, limit=limit)
