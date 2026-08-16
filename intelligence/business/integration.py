"""Native Integration Provider for Finance, Sales, Operations, and CEO Executive Briefings."""

from __future__ import annotations

from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker
from intelligence.business.engine import BusinessExecutiveEngine
from intelligence.business.tools import (
    BusinessExecutiveOverviewTool,
    BusinessFinanceAffordabilityTool,
    BusinessFinanceInvoicesTool,
    BusinessFinanceOverviewTool,
    BusinessOperationsHealthTool,
    BusinessOperationsInventoryTool,
    BusinessSalesDealsTool,
    BusinessSalesPipelineTool,
)


class BusinessIntelligenceIntegration(NativeIntegrationProvider):
    """Native provider for Finance, Sales pipeline, Operations health, and Briefings."""

    def __init__(
        self,
        engine: BusinessExecutiveEngine | None = None,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._engine = engine or BusinessExecutiveEngine()

    @property
    def engine(self) -> BusinessExecutiveEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="business_executive_hub",
            version="1.0.0",
            description=(
                "Business Executive Operating System: specialized financial runway analysis, "
                "sales pipeline tracking, operations health monitoring, and CEO briefings."
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.READ,
            enabled=True,
            rate_limits={"requests_per_minute": 120, "burst_limit": 30},
        )

    def build_tools(self) -> list[Tool]:
        return [
            BusinessExecutiveOverviewTool(self._engine),
            BusinessFinanceOverviewTool(self._engine),
            BusinessFinanceAffordabilityTool(self._engine),
            BusinessFinanceInvoicesTool(self._engine),
            BusinessSalesPipelineTool(self._engine),
            BusinessSalesDealsTool(self._engine),
            BusinessOperationsHealthTool(self._engine),
            BusinessOperationsInventoryTool(self._engine),
        ]
