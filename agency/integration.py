from __future__ import annotations

from agency.engine import AgencyAgentsEngine
from agency.tools import (
    AgencyAgentSpawnTool,
    AgencySkillsGetTool,
    AgencySkillsListTool,
    AgencySkillsMatchTool,
    AgencyTaskExecuteTool,
)
from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider


class AgencyIntegration(NativeIntegrationProvider):
    """Integration connecting the 270+ Agency Agents ecosystem into CEO OS."""

    def __init__(self, engine: AgencyAgentsEngine | None = None) -> None:
        super().__init__()
        self._engine = engine or AgencyAgentsEngine()

    @property
    def engine(self) -> AgencyAgentsEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="agency_agents",
            version="1.0.0",
            description=(
                "Deep integration of 270+ specialized Agency Agent personas, "
                "automatic skill matching, dynamic agent synthesis, and quality gates"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="agency",
            capabilities=[],
            required_credentials=[],
            rate_limits={"requests_per_minute": 300, "burst_limit": 50},
            risk_ceiling=RiskLevel.HARMLESS_WRITE,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [
            AgencySkillsListTool(self._engine),
            AgencySkillsGetTool(self._engine),
            AgencySkillsMatchTool(self._engine),
            AgencyAgentSpawnTool(self._engine),
            AgencyTaskExecuteTool(self._engine),
        ]
