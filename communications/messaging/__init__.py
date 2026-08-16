"""Universal multi-channel communications package."""

from communications.messaging.contracts import (
    FollowUpTask,
    MessageChannel,
    MessageRecipient,
    MessageRecord,
    MessageStatus,
    NotificationRecord,
    Priority,
)
from communications.messaging.integration import CommunicationsIntegration
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

__all__ = [
    "CommsConversationAnalyzeTool",
    "CommsEmailSendTool",
    "CommsFollowupScheduleTool",
    "CommsMessagesListTool",
    "CommsNotificationBroadcastTool",
    "CommsSmsSendTool",
    "CommsWhatsappSendTool",
    "CommunicationsIntegration",
    "CommunicationsManager",
    "FollowUpTask",
    "MessageChannel",
    "MessageRecipient",
    "MessageRecord",
    "MessageStatus",
    "NotificationRecord",
    "Priority",
]
