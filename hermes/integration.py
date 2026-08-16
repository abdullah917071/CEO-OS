"""Native integration provider for the Nous Hermes AI Agent subsystem."""

from __future__ import annotations

from core.contracts import RiskLevel, Tool
from hermes.agent import HermesAIAgent
from hermes.tools import (
    HermesAgentRunTool,
    HermesReflectSynthesizeTool,
    HermesSubagentSpawnTool,
    HermesTrajectoryExportTool,
)
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider


class HermesIntegration(NativeIntegrationProvider):
    """Native integration provider connecting the Nous Hermes AI Agent subsystem into CEO OS."""

    def __init__(self, agent: HermesAIAgent | None = None) -> None:
        super().__init__()
        self._agent = agent or HermesAIAgent()

    @property
    def agent(self) -> HermesAIAgent:
        return self._agent

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="hermes_agent",
            version="1.0.0",
            description=(
                "Deep integration of Nous Research Hermes 3 reasoning engine, "
                "multi-turn scratchpad function calling, reflective skill learning, "
                "and MLOps trajectory recording"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="hermes",
            capabilities=[],
            required_credentials=[],
            rate_limits={"requests_per_minute": 300, "burst_limit": 50},
            risk_ceiling=RiskLevel.HARMLESS_WRITE,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [
            HermesAgentRunTool(self._agent),
            HermesReflectSynthesizeTool(self._agent),
            HermesTrajectoryExportTool(self._agent),
            HermesSubagentSpawnTool(self._agent),
        ]
