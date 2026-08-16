"""Native Integration Provider for Universal Multi-Channel Communications."""

from __future__ import annotations

from communications.messaging.manager import CommunicationsManager
from communications.messaging.tools import (
    CommsConversationAnalyzeTool,
    CommsEmailSendTool,
    CommsFollowupScheduleTool,
    CommsMessagesListTool,
    CommsNotificationBroadcastTool,
    CommsSmsSendTool,
    CommsWhatsappSendTool,
)
from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker
from memory.service import MemoryService


class CommunicationsIntegration(NativeIntegrationProvider):
    """Native provider for Email automation, SMS, WhatsApp, Notifications, and Follow-ups."""

    def __init__(
        self,
        manager: CommunicationsManager | None = None,
        memory_service: MemoryService | None = None,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._manager = manager or CommunicationsManager(memory_service=memory_service)

    @property
    def manager(self) -> CommunicationsManager:
        return self._manager

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="communications_hub",
            version="1.0.0",
            description=(
                "Universal Communications Layer: multi-channel Email automation, SMS, "
                "WhatsApp Business messaging, executive notifications, and follow-up cadences."
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.EXTERNAL_COMMUNICATION,
            enabled=True,
            rate_limits={"requests_per_minute": 120, "burst_limit": 20},
        )

    def build_tools(self) -> list[Tool]:
        return [
            CommsEmailSendTool(self._manager),
            CommsSmsSendTool(self._manager),
            CommsWhatsappSendTool(self._manager),
            CommsNotificationBroadcastTool(self._manager),
            CommsFollowupScheduleTool(self._manager),
            CommsConversationAnalyzeTool(self._manager),
            CommsMessagesListTool(self._manager),
        ]
