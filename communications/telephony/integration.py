"""Telephony Native Integration Provider for CEO OS."""

from __future__ import annotations

from communications.telephony.contracts import TelephonyPolicy
from communications.telephony.manager import CallManager
from communications.telephony.provider import (
    DeterministicTelephonyProvider,
    TelephonyProvider,
)
from communications.telephony.tools import (
    CallStatusTool,
    OutboundCallTool,
    TerminateCallTool,
)
from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker
from memory.service import MemoryService


class TelephonyIntegration(NativeIntegrationProvider):
    """Native integration provider for the Telephony and Phone Calling subsystem."""

    def __init__(
        self,
        manager: CallManager | None = None,
        provider: TelephonyProvider | None = None,
        secret_broker: SecretBroker | None = None,
        memory_service: MemoryService | None = None,
        policy: TelephonyPolicy | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._policy = policy or TelephonyPolicy()
        if manager is not None:
            self._manager = manager
        else:
            prov = provider or DeterministicTelephonyProvider(self._policy)
            self._manager = CallManager(
                provider=prov,
                memory_service=memory_service,
                policy=self._policy,
            )

    @property
    def manager(self) -> CallManager:
        return self._manager

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="telephony",
            version="1.0.0",
            description=(
                "Telephony Subsystem: outbound calls, live conversational dialogue, "
                "transcripts, structured summaries, and call memory"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.EXTERNAL_COMMUNICATION,
            enabled=True,
            rate_limits={"requests_per_minute": 60, "burst_limit": 10},
        )

    def build_tools(self) -> list[Tool]:
        return [
            OutboundCallTool(self._manager),
            CallStatusTool(self._manager),
            TerminateCallTool(self._manager),
        ]
