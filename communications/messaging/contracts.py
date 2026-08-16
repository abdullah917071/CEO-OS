"""Data contracts and schemas for the Universal Communications subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageChannel(StrEnum):
    """Supported communication delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    NOTIFICATION = "notification"


class MessageStatus(StrEnum):
    """Message delivery lifecycle statuses."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(StrEnum):
    """Priority level for message dispatch."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class MessageRecipient:
    """Target recipient contact information across channels."""

    recipient_id: str
    name: str
    email: str | None = None
    phone: str | None = None  # E.164 standard format (+14155550199)
    whatsapp_id: str | None = None


@dataclass
class MessageRecord:
    """Record of a dispatched or scheduled communication."""

    message_id: str
    channel: MessageChannel
    recipient: MessageRecipient
    subject: str | None
    body: str
    template_id: str | None = None
    template_vars: dict[str, Any] = field(default_factory=dict)
    status: MessageStatus = MessageStatus.QUEUED
    priority: Priority = Priority.NORMAL
    scheduled_at: str | None = None
    sent_at: str | None = None
    delivered_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FollowUpTask:
    """Follow-up cadence task scheduled with a prospect, client, or executive."""

    task_id: str
    recipient: MessageRecipient
    channel: MessageChannel
    subject: str | None
    objective: str
    due_date: str
    status: str = "PENDING"  # "PENDING" | "COMPLETED" | "SNOOZED" | "CANCELLED"
    cadence_step: int = 1
    extracted_tasks: list[str] = field(default_factory=list)
    conversation_summary: str = ""


@dataclass
class NotificationRecord:
    """Broadcasted executive notification or system alert."""

    notification_id: str
    title: str
    message: str
    severity: str = "INFO"  # "INFO" | "WARNING" | "CRITICAL"
    channels_dispatched: list[MessageChannel] = field(default_factory=list)
    timestamp: str = ""
