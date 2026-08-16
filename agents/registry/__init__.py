"""Universal Agent Registry package."""

from agents.registry.agency_registry import AgentRouter, UniversalAgentRegistry
from agents.registry.contracts import (
    AgentDefinition,
    AgentDivision,
    AgentProviderProtocol,
    AgentProviderSource,
    AgentScore,
    CandidateMatch,
    TeamMemberPlan,
    TeamPlan,
)
from agents.registry.loader import AgentLoader
from agents.registry.parser import parse_agent_file
from agents.registry.providers import (
    AgencyAgentProvider,
    CustomAgentProvider,
    GeneratedAgentProvider,
    NativeAgentProvider,
)
from agents.registry.ranking import AgentRanker
from agents.registry.search import AgentSearchEngine

__all__ = [
    "AgentDefinition",
    "AgentDivision",
    "AgentLoader",
    "AgentProviderProtocol",
    "AgentProviderSource",
    "AgentRanker",
    "AgentRouter",
    "AgentScore",
    "AgentSearchEngine",
    "AgencyAgentProvider",
    "CandidateMatch",
    "CustomAgentProvider",
    "GeneratedAgentProvider",
    "NativeAgentProvider",
    "TeamMemberPlan",
    "TeamPlan",
    "UniversalAgentRegistry",
    "parse_agent_file",
]
