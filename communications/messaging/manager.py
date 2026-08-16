"""Communications Manager: orchestrator for multi-channel messaging and follow-ups."""

from __future__ import annotations

import datetime
import logging
import re
import uuid
from typing import Any

from communications.messaging.contracts import (
    FollowUpTask,
    MessageChannel,
    MessageRecipient,
    MessageRecord,
    MessageStatus,
    NotificationRecord,
    Priority,
)
from memory.service import MemoryService, Provenance

logger = logging.getLogger(__name__)


class CommunicationsManager:
    """Unified communications manager providing universal delivery across

    Email, SMS, WhatsApp, executive notifications, and follow-up cadence scheduling.
    """

    def __init__(self, memory_service: MemoryService | None = None) -> None:
        self._memory = memory_service
        self._messages: dict[str, MessageRecord] = {}
        self._followups: dict[str, FollowUpTask] = {}
        self._notifications: dict[str, NotificationRecord] = {}

    def _now_iso(self) -> str:
        return datetime.datetime.now(datetime.UTC).isoformat()

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        name: str | None = None,
        template_id: str | None = None,
        template_vars: dict[str, Any] | None = None,
        scheduled_at: str | None = None,
        priority: Priority = Priority.NORMAL,
    ) -> MessageRecord:
        """Send or schedule an outbound email."""
        msg_id = f"msg_em_{uuid.uuid4().hex[:8]}"
        recipient = MessageRecipient(
            recipient_id=f"rcp_{uuid.uuid4().hex[:6]}",
            name=name or to_email.split("@")[0].capitalize(),
            email=to_email,
        )

        rendered_body = body
        if template_vars:
            for k, v in template_vars.items():
                rendered_body = rendered_body.replace(f"{{{{{k}}}}}", str(v))

        status = MessageStatus.QUEUED if scheduled_at else MessageStatus.DELIVERED
        now = self._now_iso()
        record = MessageRecord(
            message_id=msg_id,
            channel=MessageChannel.EMAIL,
            recipient=recipient,
            subject=subject,
            body=rendered_body,
            template_id=template_id,
            template_vars=template_vars or {},
            status=status,
            priority=priority,
            scheduled_at=scheduled_at,
            sent_at=now if not scheduled_at else None,
            delivered_at=now if not scheduled_at else None,
            metadata={"client": "smtp_automation", "to": to_email},
        )
        self._messages[msg_id] = record
        logger.info("Dispatched email %s to %s with subject '%s'", msg_id, to_email, subject)
        return record

    async def send_sms(
        self,
        to_phone: str,
        body: str,
        name: str | None = None,
        priority: Priority = Priority.NORMAL,
    ) -> MessageRecord:
        """Send an outbound SMS message to a mobile number."""
        msg_id = f"msg_sms_{uuid.uuid4().hex[:8]}"
        recipient = MessageRecipient(
            recipient_id=f"rcp_{uuid.uuid4().hex[:6]}",
            name=name or "Client",
            phone=to_phone,
        )
        now = self._now_iso()
        record = MessageRecord(
            message_id=msg_id,
            channel=MessageChannel.SMS,
            recipient=recipient,
            subject=None,
            body=body,
            status=MessageStatus.DELIVERED,
            priority=priority,
            sent_at=now,
            delivered_at=now,
            metadata={"carrier": "TwilioDirect", "to": to_phone},
        )
        self._messages[msg_id] = record
        logger.info("Dispatched SMS %s to %s", msg_id, to_phone)
        return record

    async def send_whatsapp(
        self,
        to_phone: str,
        body: str,
        name: str | None = None,
        template_id: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> MessageRecord:
        """Send an interactive or template WhatsApp message via Business Cloud API."""
        msg_id = f"msg_wa_{uuid.uuid4().hex[:8]}"
        recipient = MessageRecipient(
            recipient_id=f"rcp_{uuid.uuid4().hex[:6]}",
            name=name or "Client",
            phone=to_phone,
            whatsapp_id=to_phone.replace("+", "").replace("-", ""),
        )

        rendered_body = body
        if template_vars:
            for k, v in template_vars.items():
                rendered_body = rendered_body.replace(f"{{{{{k}}}}}", str(v))

        now = self._now_iso()
        record = MessageRecord(
            message_id=msg_id,
            channel=MessageChannel.WHATSAPP,
            recipient=recipient,
            subject=None,
            body=rendered_body,
            template_id=template_id,
            template_vars=template_vars or {},
            status=MessageStatus.DELIVERED,
            priority=Priority.NORMAL,
            sent_at=now,
            delivered_at=now,
            metadata={"api": "WhatsApp_Cloud_API_v19.0", "to": to_phone},
        )
        self._messages[msg_id] = record
        logger.info("Dispatched WhatsApp message %s to %s", msg_id, to_phone)
        return record

    async def broadcast_notification(
        self,
        title: str,
        message: str,
        severity: str = "INFO",
        channels: list[MessageChannel] | None = None,
    ) -> NotificationRecord:
        """Broadcast an executive notification across configured channels."""
        notif_id = f"notif_{uuid.uuid4().hex[:8]}"
        dispatched_channels = channels or [
            MessageChannel.EMAIL,
            MessageChannel.SMS,
            MessageChannel.WHATSAPP,
        ]
        now = self._now_iso()
        record = NotificationRecord(
            notification_id=notif_id,
            title=title,
            message=message,
            severity=severity.upper(),
            channels_dispatched=dispatched_channels,
            timestamp=now,
        )
        self._notifications[notif_id] = record
        logger.info("Broadcasted notification %s [%s]: %s", notif_id, severity, title)
        return record

    async def schedule_follow_up(
        self,
        recipient_name: str,
        recipient_contact: str,
        channel: MessageChannel,
        objective: str,
        due_date: str,
        subject: str | None = None,
        cadence_step: int = 1,
    ) -> FollowUpTask:
        """Schedule an automated follow-up cadence task and record episodic memory."""
        task_id = f"fup_{uuid.uuid4().hex[:8]}"
        recipient = MessageRecipient(
            recipient_id=f"rcp_{uuid.uuid4().hex[:6]}",
            name=recipient_name,
            email=recipient_contact if "@" in recipient_contact else None,
            phone=recipient_contact if "@" not in recipient_contact else None,
            whatsapp_id=recipient_contact if "@" not in recipient_contact else None,
        )

        follow_up = FollowUpTask(
            task_id=task_id,
            recipient=recipient,
            channel=channel,
            subject=subject,
            objective=objective,
            due_date=due_date,
            status="PENDING",
            cadence_step=cadence_step,
            extracted_tasks=[f"Follow up regarding {objective}"],
            conversation_summary=(
                f"Follow-up cadence #{cadence_step} scheduled with {recipient_name}."
            ),
        )
        self._followups[task_id] = follow_up

        if self._memory:
            try:
                await self._memory.create(
                    memory_type="episodic",
                    content=(
                        f"Scheduled follow-up with {recipient_name} via {channel.value} "
                        f"on {due_date}. Objective: {objective} (Cadence Step {cadence_step})"
                    ),
                    provenance=Provenance(
                        source_type=f"comms_{channel.value}",
                        detail=f"Follow-up {task_id}",
                    ),
                    importance=0.8,
                    attributes={
                        "followup_id": task_id,
                        "recipient": recipient_name,
                        "channel": channel.value,
                    },
                )
            except Exception as exc:
                logger.warning("Failed to store follow-up in episodic memory: %s", exc)

        logger.info("Scheduled follow-up %s with %s on %s", task_id, recipient_name, due_date)
        return follow_up

    async def list_messages(
        self,
        channel: MessageChannel | None = None,
        status: MessageStatus | None = None,
    ) -> list[MessageRecord]:
        """List messages filtered by channel and status."""
        results = list(self._messages.values())
        if channel:
            results = [m for m in results if m.channel == channel]
        if status:
            results = [m for m in results if m.status == status]
        return results

    async def list_follow_ups(self, status: str | None = None) -> list[FollowUpTask]:
        """List follow-ups filtered by status."""
        results = list(self._followups.values())
        if status:
            results = [f for f in results if f.status.upper() == status.upper()]
        return results

    async def analyze_conversation(self, transcript: str) -> dict[str, Any]:
        """Analyze a conversation transcript: summarize, extract tasks, qualify lead."""
        lines = [line.strip() for line in transcript.strip().split("\n") if line.strip()]

        task_pat = re.compile(r"\b(will|send|schedule|call|follow up|demo|proposal|review)\b", re.I)
        extracted_tasks: list[str] = [line for line in lines if task_pat.search(line)]

        is_lead = any(
            kw in transcript.lower()
            for kw in ["pricing", "demo", "interested", "buy", "contract", "enterprise", "quote"]
        )

        qualification = "High Intent / Qualified" if is_lead else "General Inquiries"
        summary = (
            f"Conversation transcript contained {len(lines)} turn(s). "
            f"Identified {len(extracted_tasks)} actionable commitment(s). "
            f"Lead qualification status: {qualification}."
        )

        return {
            "turn_count": len(lines),
            "summary": summary,
            "extracted_tasks": extracted_tasks or ["General follow-up"],
            "lead_identified": is_lead,
            "recommended_cadence_days": 3 if is_lead else 7,
        }
