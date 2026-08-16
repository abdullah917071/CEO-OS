"""Native Integration Provider for Marketing Intelligence and Multi-Channel Attribution."""

from __future__ import annotations

from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker
from intelligence.marketing.engine import MarketingIntelligenceEngine
from intelligence.marketing.tools import (
    MarketingAttributionFunnelTool,
    MarketingCreativesAnalyzeTool,
    MarketingProfitDiagnoseTool,
    MarketingSnapshotGetTool,
)


class MarketingIntelligenceIntegration(NativeIntegrationProvider):
    """Native provider supplying cross-channel marketing intelligence and profit diagnostics."""

    def __init__(
        self,
        engine: MarketingIntelligenceEngine | None = None,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._engine = engine or MarketingIntelligenceEngine()

    @property
    def engine(self) -> MarketingIntelligenceEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="marketing_intelligence",
            version="1.0.0",
            description=(
                "Unified Marketing Intelligence and Cross-Channel Attribution: "
                "combines Meta Ads, Google Analytics, CRM, and Sales data for profit diagnostics."
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.READ,
            enabled=True,
            rate_limits={"requests_per_minute": 60, "burst_limit": 10},
        )

    def build_tools(self) -> list[Tool]:
        return [
            MarketingProfitDiagnoseTool(self._engine),
            MarketingAttributionFunnelTool(self._engine),
            MarketingCreativesAnalyzeTool(self._engine),
            MarketingSnapshotGetTool(self._engine),
        ]
