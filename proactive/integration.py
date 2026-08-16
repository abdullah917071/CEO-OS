from __future__ import annotations

from core.contracts import RiskLevel, Tool
from integrations.contracts import (
    IntegrationManifest,
    IntegrationType,
)
from integrations.native import NativeIntegrationProvider
from proactive.engine import ProactiveCeoEngine
from proactive.tools import (
    ProactiveEvaluateTool,
    ProactiveGoalCreateTool,
    ProactiveGoalListTool,
    ProactiveInsightsGetTool,
    ProactiveTriggerCreateTool,
    ProactiveTriggerListTool,
)


class ProactiveIntegration(NativeIntegrationProvider):
    """Native integration provider for the Proactive CEO subsystem."""

    def __init__(self, engine: ProactiveCeoEngine | None = None) -> None:
        super().__init__()
        self._engine = engine or ProactiveCeoEngine()

    @property
    def engine(self) -> ProactiveCeoEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="proactive_ceo",
            version="1.0.0",
            description=(
                "Proactive CEO engine for continuous business observation, "
                "event triggers, goal tracking, and recommendations"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="intelligence",
            capabilities=[],
            required_credentials=[],
            rate_limits={"requests_per_minute": 120, "burst_limit": 30},
            risk_ceiling=RiskLevel.HARMLESS_WRITE,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [
            ProactiveEvaluateTool(self._engine),
            ProactiveInsightsGetTool(self._engine),
            ProactiveTriggerCreateTool(self._engine),
            ProactiveTriggerListTool(self._engine),
            ProactiveGoalCreateTool(self._engine),
            ProactiveGoalListTool(self._engine),
        ]
