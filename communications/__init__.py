"""Provider-neutral messaging and telephony subsystem."""

from communications.messaging import (
    CommunicationsIntegration,
    CommunicationsManager,
    FollowUpTask,
    MessageChannel,
    MessageRecipient,
    MessageRecord,
    MessageStatus,
    NotificationRecord,
    Priority,
)
from communications.telephony import (
    CallManager,
    CallRecord,
    CallStatus,
    TelephonyIntegration,
    TelephonyPolicy,
    TelephonyProvider,
)

__all__ = [
    "CallManager",
    "CallRecord",
    "CallStatus",
    "CommunicationsIntegration",
    "CommunicationsManager",
    "FollowUpTask",
    "MessageChannel",
    "MessageRecipient",
    "MessageRecord",
    "MessageStatus",
    "NotificationRecord",
    "Priority",
    "TelephonyIntegration",
    "TelephonyPolicy",
    "TelephonyProvider",
]
