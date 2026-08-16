"""Capability tools for the Universal Communications Layer."""

from __future__ import annotations

import dataclasses
from typing import Any

from communications.messaging.contracts import (
    MessageChannel,
    MessageStatus,
    Priority,
)
from communications.messaging.manager import CommunicationsManager
from core.contracts import CapabilitySpec, RiskLevel, ToolResult


class CommsEmailSendTool:
    """Tool to compose, schedule, or send an email."""

    def __init__(self, manager: CommunicationsManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="comms.email.send",
            description="Send or schedule an outbound email with templates and variable support",
            input_schema={
                "type": "object",
                "properties": {
                    "to_email": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body content"},
                    "name": {"type": "string", "description": "Optional recipient name"},
                    "template_id": {"type": "string", "description": "Optional template ID"},
                    "template_vars": {"type": "object", "description": "Template variables"},
                    "scheduled_at": {"type": "string", "description": "ISO timestamp to schedule"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "default": "normal",
                    },
                },
                "required": ["to_email", "subject", "body"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:comms",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        to_email = str(arguments["to_email"])
        subject = str(arguments["subject"])
        body = str(arguments["body"])
        name = arguments.get("name")
        template_id = arguments.get("template_id")
        template_vars = arguments.get("template_vars")
        scheduled_at = arguments.get("scheduled_at")
        priority_str = str(arguments.get("priority", "normal")).lower()
        priority = (
            Priority(priority_str)
            if priority_str in Priority._value2member_map_
            else Priority.NORMAL
        )

        record = await self._manager.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            name=name,
            template_id=template_id,
            template_vars=template_vars,
            scheduled_at=scheduled_at,
            priority=priority,
        )
        return ToolResult(
            output=dataclasses.asdict(record),
            evidence=[f"Email '{record.subject}' ({record.message_id}) sent to {to_email}"],
        )


class CommsSmsSendTool:
    """Tool to send an SMS text message."""

    def __init__(self, manager: CommunicationsManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="comms.sms.send",
            description="Send an outbound SMS message to a mobile phone number",
            input_schema={
                "type": "object",
                "properties": {
                    "to_phone": {"type": "string", "description": "E.164 phone number"},
                    "body": {"type": "string", "description": "SMS message body"},
                    "name": {"type": "string", "description": "Optional recipient name"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "default": "normal",
                    },
                },
                "required": ["to_phone", "body"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:comms",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        to_phone = str(arguments["to_phone"])
        body = str(arguments["body"])
        name = arguments.get("name")
        priority_str = str(arguments.get("priority", "normal")).lower()
        priority = (
            Priority(priority_str)
            if priority_str in Priority._value2member_map_
            else Priority.NORMAL
        )

        record = await self._manager.send_sms(
            to_phone=to_phone,
            body=body,
            name=name,
            priority=priority,
        )
        return ToolResult(
            output=dataclasses.asdict(record),
            evidence=[f"SMS ({record.message_id}) delivered to {to_phone}"],
        )


class CommsWhatsappSendTool:
    """Tool to send a WhatsApp Business message."""

    def __init__(self, manager: CommunicationsManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="comms.whatsapp.send",
            description="Send a WhatsApp Business message to a phone number",
            input_schema={
                "type": "object",
                "properties": {
                    "to_phone": {"type": "string", "description": "E.164 phone number"},
                    "body": {"type": "string", "description": "Message text"},
                    "name": {"type": "string", "description": "Optional recipient name"},
                    "template_id": {"type": "string", "description": "Optional template ID"},
                    "template_vars": {"type": "object", "description": "Template variables"},
                },
                "required": ["to_phone", "body"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:comms",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        to_phone = str(arguments["to_phone"])
        body = str(arguments["body"])
        name = arguments.get("name")
        template_id = arguments.get("template_id")
        template_vars = arguments.get("template_vars")

        record = await self._manager.send_whatsapp(
            to_phone=to_phone,
            body=body,
            name=name,
            template_id=template_id,
            template_vars=template_vars,
        )
        return ToolResult(
            output=dataclasses.asdict(record),
            evidence=[f"WhatsApp message ({record.message_id}) delivered to {to_phone}"],
        )


class CommsNotificationBroadcastTool:
    """Tool to broadcast multi-channel executive notifications."""

    def __init__(self, manager: CommunicationsManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="comms.notification.broadcast",
            description="Broadcast an executive alert across email, SMS, and WhatsApp",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Alert title"},
                    "message": {"type": "string", "description": "Detailed notification message"},
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "critical"],
                        "default": "info",
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Channels (email, sms, whatsapp)",
                    },
                },
                "required": ["title", "message"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:comms",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        title = str(arguments["title"])
        message = str(arguments["message"])
        severity = str(arguments.get("severity", "info"))
        ch_list = arguments.get("channels")
        channels: list[MessageChannel] | None = None
        if ch_list and isinstance(ch_list, list):
            channels = [
                MessageChannel(c.lower())
                for c in ch_list
                if c.lower() in MessageChannel._value2member_map_
            ]

        record = await self._manager.broadcast_notification(
            title=title,
            message=message,
            severity=severity,
            channels=channels,
        )
        return ToolResult(
            output=dataclasses.asdict(record),
            evidence=[
                f"Notification '{record.title}' [{record.severity}] broadcasted across "
                + ", ".join(c.value for c in record.channels_dispatched)
            ],
        )


class CommsFollowupScheduleTool:
    """Tool to schedule an automated follow-up cadence."""

    def __init__(self, manager: CommunicationsManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="comms.followup.schedule",
            description="Schedule an automated follow-up cadence with a client, lead, or partner",
            input_schema={
                "type": "object",
                "properties": {
                    "recipient_name": {"type": "string", "description": "Recipient name"},
                    "recipient_contact": {
                        "type": "string",
                        "description": "Email or phone number",
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["email", "sms", "whatsapp"],
                        "default": "whatsapp",
                    },
                    "objective": {"type": "string", "description": "Goal of the follow-up"},
                    "due_date": {
                        "type": "string",
                        "description": "Due date (e.g. 2026-08-19 or 'in 3 days')",
                    },
                    "subject": {"type": "string", "description": "Optional topic or subject"},
                    "cadence_step": {"type": "integer", "default": 1},
                },
                "required": ["recipient_name", "recipient_contact", "objective", "due_date"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:comms",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        recipient_name = str(arguments["recipient_name"])
        recipient_contact = str(arguments["recipient_contact"])
        ch_str = str(arguments.get("channel", "whatsapp")).lower()
        channel = (
            MessageChannel(ch_str)
            if ch_str in MessageChannel._value2member_map_
            else MessageChannel.WHATSAPP
        )
        objective = str(arguments["objective"])
        due_date = str(arguments["due_date"])
        subject = arguments.get("subject")
        cadence_step = int(arguments.get("cadence_step", 1))

        task = await self._manager.schedule_follow_up(
            recipient_name=recipient_name,
            recipient_contact=recipient_contact,
            channel=channel,
            objective=objective,
            due_date=due_date,
            subject=subject,
            cadence_step=cadence_step,
        )
        return ToolResult(
            output=dataclasses.asdict(task),
            evidence=[
                f"Follow-up task '{task.task_id}' scheduled with {recipient_name} "
                f"via {channel.value} on {due_date} (Step {cadence_step})"
            ],
        )


class CommsConversationAnalyzeTool:
    """Tool to analyze a transcript for action items and lead qualification."""

    def __init__(self, manager: CommunicationsManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="comms.conversation.analyze",
            description="Analyze conversation transcript to summarize and extract action items",
            input_schema={
                "type": "object",
                "properties": {
                    "transcript": {"type": "string", "description": "Raw transcript text"},
                },
                "required": ["transcript"],
            },
            risk=RiskLevel.READ,
            source="integration:comms",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        transcript = str(arguments["transcript"])
        analysis = await self._manager.analyze_conversation(transcript)
        return ToolResult(
            output=analysis,
            evidence=[
                f"Conversation Analysis: {analysis['summary']}; "
                f"{len(analysis['extracted_tasks'])} action items extracted"
            ],
        )


class CommsMessagesListTool:
    """Tool to inspect message delivery history."""

    def __init__(self, manager: CommunicationsManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="comms.messages.list",
            description="List message delivery history across email, SMS, and WhatsApp",
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Optional channel filter"},
                    "status": {"type": "string", "description": "Optional status filter"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:comms",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        ch_str = arguments.get("channel")
        channel = (
            MessageChannel(ch_str.lower())
            if ch_str and ch_str.lower() in MessageChannel._value2member_map_
            else None
        )
        st_str = arguments.get("status")
        status = (
            MessageStatus(st_str.lower())
            if st_str and st_str.lower() in MessageStatus._value2member_map_
            else None
        )

        messages = await self._manager.list_messages(channel=channel, status=status)
        return ToolResult(
            output=[dataclasses.asdict(m) for m in messages],
            evidence=[f"Found {len(messages)} message record(s) in communications history"],
        )
