"""Native integration provider for the Restaurant Booking Workflow."""

from __future__ import annotations

from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker
from workflows.restaurant.tools import RestaurantBookingTool
from workflows.restaurant.workflow import RestaurantBookingWorkflow


class RestaurantWorkflowIntegration(NativeIntegrationProvider):
    """Native integration provider for the multi-service Restaurant Booking Workflow."""

    def __init__(
        self,
        workflow: RestaurantBookingWorkflow | None = None,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._workflow = workflow or RestaurantBookingWorkflow()

    @property
    def workflow(self) -> RestaurantBookingWorkflow:
        return self._workflow

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="restaurant_workflow",
            version="1.0.0",
            description=(
                "Autonomous Restaurant Booking Workflow: orchestrates Places search, "
                "Telephony calling, Calendar scheduling, and Episodic Memory"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.EXTERNAL_COMMUNICATION,
            enabled=True,
            rate_limits={"requests_per_minute": 60, "burst_limit": 10},
        )

    def build_tools(self) -> list[Tool]:
        return [
            RestaurantBookingTool(self._workflow),
        ]
