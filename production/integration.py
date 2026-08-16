from __future__ import annotations

from core.contracts import RiskLevel, Tool
from integrations.contracts import (
    IntegrationManifest,
    IntegrationType,
)
from integrations.native import NativeIntegrationProvider
from production.engine import ProductionHardeningEngine
from production.tools import (
    ProductionAgentPerformanceTool,
    ProductionConfidenceVerifyTool,
    ProductionCostOverviewTool,
    ProductionResilienceHealthTool,
    ProductionSecurityAuditTool,
)


class ProductionHardeningIntegration(NativeIntegrationProvider):
    """Native integration provider for the Production Hardening subsystem."""

    def __init__(self, engine: ProductionHardeningEngine | None = None) -> None:
        super().__init__()
        self._engine = engine or ProductionHardeningEngine()

    @property
    def engine(self) -> ProductionHardeningEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="production_hardening",
            version="1.0.0",
            description=(
                "Production hardening engine for security auditing, FinOps cost tracking, "
                "agent performance monitoring, confidence verification, and operational resilience"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="operations",
            capabilities=[],
            required_credentials=[],
            rate_limits={"requests_per_minute": 120, "burst_limit": 30},
            risk_ceiling=RiskLevel.READ,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [
            ProductionSecurityAuditTool(self._engine),
            ProductionCostOverviewTool(self._engine),
            ProductionAgentPerformanceTool(self._engine),
            ProductionConfidenceVerifyTool(self._engine),
            ProductionResilienceHealthTool(self._engine),
        ]
