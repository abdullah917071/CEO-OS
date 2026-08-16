"""Native integration provider for the CEO OS Executive AI Agent subsystem."""

from __future__ import annotations

from ceo_agent.agent import CeoAIAgent
from ceo_agent.tools import (
    CeoAgentRunTool,
    CeoReflectSynthesizeTool,
    CeoSubagentSpawnTool,
    CeoTrajectoryExportTool,
)
from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider


class CeoExecutiveIntegration(NativeIntegrationProvider):
    """Native integration provider connecting the CEO OS Executive Agent."""

    def __init__(self, agent: CeoAIAgent | None = None) -> None:
        super().__init__()
        self._agent = agent or CeoAIAgent()

    @property
    def agent(self) -> CeoAIAgent:
        return self._agent

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="ceo_agent",
            version="1.0.0",
            description=(
                "CEO OS Central Executive AI Agent with ReAct reasoning, "
                "multi-turn scratchpad tool calling, reflective skill learning, "
                "and MLOps trajectory recording"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="ceo_agent",
            capabilities=[],
            required_credentials=[],
            rate_limits={"requests_per_minute": 300, "burst_limit": 50},
            risk_ceiling=RiskLevel.HARMLESS_WRITE,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [
            CeoAgentRunTool(self._agent),
            CeoReflectSynthesizeTool(self._agent),
            CeoTrajectoryExportTool(self._agent),
            CeoSubagentSpawnTool(self._agent),
        ]


# Backwards compatibility alias
HermesIntegration = CeoExecutiveIntegration
