"""Native Integration Provider exposing Developer Agent API Auto-Builder capabilities."""

from __future__ import annotations

from core.contracts import RiskLevel, Tool
from integrations.autobuilder.engine import ApiAutoBuilderEngine
from integrations.autobuilder.tools import (
    ApiIngestTool,
    ApiInspectTool,
    ApiListTool,
    ApiTestTool,
)
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker


class ApiAutoBuilderIntegration(NativeIntegrationProvider):
    """Native provider enabling dynamic API specification ingestion and capability synthesis."""

    def __init__(
        self,
        engine: ApiAutoBuilderEngine | None = None,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._engine = engine or ApiAutoBuilderEngine(secret_broker=secret_broker)

    @property
    def engine(self) -> ApiAutoBuilderEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="api_auto_builder",
            version="1.0.0",
            description=(
                "Developer Agent API Auto-Builder: dynamic ingestion of OpenAPI/Swagger "
                "specifications, sandbox test generation, and live capability registration."
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.HARMLESS_WRITE,
            enabled=True,
            rate_limits={"requests_per_minute": 60, "burst_limit": 20},
        )

    def build_tools(self) -> list[Tool]:
        return [
            ApiIngestTool(self._engine),
            ApiTestTool(self._engine),
            ApiInspectTool(self._engine),
            ApiListTool(self._engine),
        ]
