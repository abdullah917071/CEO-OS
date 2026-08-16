"""Contracts and data models for Universal Agent Registry, Router, and Scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class AgentDivision(StrEnum):
    ENGINEERING = "engineering"
    MARKETING = "marketing"
    SALES = "sales"
    FINANCE = "finance"
    OPERATIONS = "operations"
    PRODUCT = "product"
    SECURITY = "security"
    DESIGN = "design"
    RESEARCH = "research"
    COMMUNICATIONS = "communications"
    GENERAL = "general"


class AgentProviderSource(StrEnum):
    NATIVE = "native"
    AGENCY = "agency-agents"
    CUSTOM = "custom"
    GENERATED = "generated"


@dataclass(slots=True)
class AgentScore:
    """Historical performance metrics for an agent persona."""

    tasks_completed: int = 0
    success_rate: float = 1.0
    average_confidence: float = 0.90
    average_cost: float = 1.0
    average_latency_ms: float = 500.0
    owner_rating: float = 5.0  # 1.0 to 5.0
    failure_rate: float = 0.0

    def record_outcome(
        self,
        success: bool,
        confidence: float = 0.90,
        cost: float = 1.0,
        latency_ms: float = 500.0,
        rating: float | None = None,
    ) -> None:
        self.tasks_completed += 1
        n = self.tasks_completed
        # Rolling averages
        self.success_rate = ((self.success_rate * (n - 1)) + (1.0 if success else 0.0)) / n
        self.failure_rate = 1.0 - self.success_rate
        self.average_confidence = ((self.average_confidence * (n - 1)) + confidence) / n
        self.average_cost = ((self.average_cost * (n - 1)) + cost) / n
        self.average_latency_ms = ((self.average_latency_ms * (n - 1)) + latency_ms) / n
        if rating is not None:
            self.owner_rating = ((self.owner_rating * (n - 1)) + rating) / n


@dataclass(slots=True)
class AgentDefinition:
    """Full canonical definition of an agent persona in the Universal Registry."""

    id: str  # e.g. "product-manager", "agency-finops-engineer", "developer-director"
    name: str  # e.g. "Product Manager", "FinOps Engineer"
    division: AgentDivision
    role: str
    description: str
    instructions: str
    source: AgentProviderSource = AgentProviderSource.AGENCY
    tags: list[str] = field(default_factory=list)
    default_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    allowed_capabilities: list[str] = field(default_factory=list)
    model_class: str = "medium_reasoning"
    is_permanent: bool = False
    score: AgentScore = field(default_factory=AgentScore)
    metadata: dict[str, Any] = field(default_factory=dict)
    file_path: str | None = None


@dataclass(slots=True)
class CandidateMatch:
    """A scored agent candidate from search/ranking."""

    agent: AgentDefinition
    relevance_score: float  # 0.0 to 1.0
    match_reasons: list[str] = field(default_factory=list)
    suggested_tools: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TeamMemberPlan:
    """Role and assignment of a team member in a multi-agent team."""

    agent_id: str
    role_in_team: str  # e.g. "lead", "design", "implementation", "verification", "synthesis"
    assigned_subtasks: list[str] = field(default_factory=list)
    depends_on_agents: list[str] = field(default_factory=list)
    assigned_tools: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TeamPlan:
    """Coordinated multi-agent plan for complex objectives."""

    objective: str
    lead_agent_id: str
    members: list[TeamMemberPlan] = field(default_factory=list)
    execution_order: list[list[str]] = field(default_factory=list)  # Parallel stages
    estimated_cost: float = 0.0
    constraints: dict[str, Any] = field(default_factory=dict)


class AgentProviderProtocol(Protocol):
    """Protocol implemented by each agent source provider."""

    @property
    def source(self) -> AgentProviderSource: ...

    async def list_agents(self) -> list[AgentDefinition]: ...

    async def get_agent(self, agent_id: str) -> AgentDefinition | None: ...

    async def search(
        self, query: str, division: AgentDivision | None = None, limit: int = 10
    ) -> list[CandidateMatch]: ...
