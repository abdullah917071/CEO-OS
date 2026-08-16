import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.src.ceo_os_api.main import app
from communications.messaging.contracts import (
    MessageChannel,
    MessageStatus,
    Priority,
)
from communications.messaging.integration import CommunicationsIntegration
from communications.messaging.manager import CommunicationsManager
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.router import CapabilityRouter
from memory.embedding import FeatureHashEmbeddingProvider
from memory.service import MemoryService, initialize_memory_schema


def test_communications_manifest_and_tool_registration() -> None:
    integration = CommunicationsIntegration()
    manifest = integration.manifest()

    assert manifest.name == "communications_hub"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.EXTERNAL_COMMUNICATION

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 7
    tool_names = {t.spec.name for t in tools}
    expected = {
        "comms.email.send",
        "comms.sms.send",
        "comms.whatsapp.send",
        "comms.notification.broadcast",
        "comms.followup.schedule",
        "comms.conversation.analyze",
        "comms.messages.list",
    }
    assert expected.issubset(tool_names)

    r2_tools = {
        "comms.email.send",
        "comms.sms.send",
        "comms.whatsapp.send",
        "comms.notification.broadcast",
        "comms.followup.schedule",
    }
    for tool in tools:
        if tool.spec.name in r2_tools:
            assert tool.spec.risk == RiskLevel.EXTERNAL_COMMUNICATION
        else:
            assert tool.spec.risk == RiskLevel.READ


@pytest.mark.asyncio
async def test_communications_email_lifecycle() -> None:
    manager = CommunicationsManager()

    # 1. Immediate email with template
    rec = await manager.send_email(
        to_email="founder@acme.corp",
        subject="Welcome to CEO OS",
        body="Hello {{name}}, welcome to {{tier}} edition.",
        template_vars={"name": "Alex", "tier": "Enterprise"},
    )
    assert rec.message_id.startswith("msg_em_")
    assert rec.status == MessageStatus.DELIVERED
    assert "Hello Alex, welcome to Enterprise edition." in rec.body

    # 2. Scheduled email
    sched = await manager.send_email(
        to_email="board@acme.corp",
        subject="Monthly Briefing",
        body="Attached please find the monthly brief.",
        scheduled_at="2026-09-01T09:00:00Z",
    )
    assert sched.status == MessageStatus.QUEUED
    assert sched.scheduled_at == "2026-09-01T09:00:00Z"


@pytest.mark.asyncio
async def test_communications_sms_and_whatsapp_lifecycle() -> None:
    manager = CommunicationsManager()

    # 1. Outbound SMS
    sms = await manager.send_sms(
        to_phone="+1-415-555-0100",
        body="Your verification code is 849201",
        priority=Priority.HIGH,
    )
    assert sms.channel == MessageChannel.SMS
    assert sms.status == MessageStatus.DELIVERED
    assert sms.priority == Priority.HIGH

    # 2. WhatsApp Message
    wa = await manager.send_whatsapp(
        to_phone="+1-415-555-0199",
        body="Hello {{name}}, your demo is confirmed.",
        template_vars={"name": "Sarah"},
    )
    assert wa.channel == MessageChannel.WHATSAPP
    assert wa.status == MessageStatus.DELIVERED
    assert "Hello Sarah, your demo is confirmed." in wa.body


@pytest.mark.asyncio
async def test_communications_notification_broadcast() -> None:
    manager = CommunicationsManager()
    notif = await manager.broadcast_notification(
        title="APAC Database Failover",
        message="Primary database failed over to replica successfully.",
        severity="WARNING",
    )
    assert notif.notification_id.startswith("notif_")
    assert notif.severity == "WARNING"
    assert len(notif.channels_dispatched) == 3


@pytest.mark.asyncio
async def test_communications_followup_and_memory(tmp_path: Path) -> None:
    db_path = tmp_path / "comms_mem.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    await initialize_memory_schema(engine)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedder = FeatureHashEmbeddingProvider()
    mem = MemoryService(session_factory, "sqlite", embedder)

    manager = CommunicationsManager(memory_service=mem)
    follow_up = await manager.schedule_follow_up(
        recipient_name="Sarah Chen",
        recipient_contact="+1-415-555-0199",
        channel=MessageChannel.WHATSAPP,
        objective="Review Enterprise Contract",
        due_date="2026-08-19",
        cadence_step=1,
    )
    assert follow_up.task_id.startswith("fup_")
    assert follow_up.status == "PENDING"
    assert follow_up.cadence_step == 1

    # Verify episodic memory was recorded
    memories = await mem.search("Sarah Chen WhatsApp follow-up", memory_type="episodic")
    assert len(memories) >= 1
    assert "Sarah Chen" in memories[0].content

    await engine.dispose()


@pytest.mark.asyncio
async def test_communications_conversation_analysis() -> None:
    manager = CommunicationsManager()
    transcript = (
        "Client: We are very interested in enterprise pricing and demo for 50 users.\n"
        "Agent: I will send over the customized proposal today.\n"
        "Client: Great, let's schedule a follow up on Friday."
    )
    analysis = await manager.analyze_conversation(transcript)
    assert analysis["turn_count"] == 3
    assert analysis["lead_identified"] is True
    assert len(analysis["extracted_tasks"]) >= 1
    assert "Conversation transcript" in analysis["summary"]


def test_capability_router_communications_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains("Send WhatsApp message to client")
    assert "integrations" in domains

    sms_domains = router.classify_domains("Send SMS verification code")
    assert "integrations" in sms_domains

    followup_domains = router.classify_domains("Schedule follow-up cadence in 3 days")
    assert "integrations" in followup_domains


def test_api_communications_endpoints() -> None:
    with TestClient(app) as client:
        # 1. Send Email
        em_resp = client.post(
            "/api/v1/comms/email",
            json={
                "to_email": "cto@partner.io",
                "subject": "Integration Kickoff",
                "body": "Looking forward to our integration session.",
            },
        )
        assert em_resp.status_code == 201
        assert em_resp.json()["status"] == "delivered"

        # 2. Send SMS
        sms_resp = client.post(
            "/api/v1/comms/sms",
            json={
                "to_phone": "+1-415-555-0100",
                "body": "System update scheduled for 10 PM UTC.",
            },
        )
        assert sms_resp.status_code == 201

        # 3. Send WhatsApp
        wa_resp = client.post(
            "/api/v1/comms/whatsapp",
            json={
                "to_phone": "+1-415-555-0199",
                "body": "Your demo is confirmed for Friday.",
            },
        )
        assert wa_resp.status_code == 201

        # 4. Broadcast Notification
        notif_resp = client.post(
            "/api/v1/comms/notifications",
            json={
                "title": "API Latency Normalized",
                "message": "All latency spikes resolved across regions.",
                "severity": "info",
            },
        )
        assert notif_resp.status_code == 201

        # 5. Schedule Follow-up
        fup_resp = client.post(
            "/api/v1/comms/followups",
            json={
                "recipient_name": "Michael Scott",
                "recipient_contact": "+1-415-555-0122",
                "channel": "whatsapp",
                "objective": "Q3 Demo and Proposal Follow-up",
                "due_date": "2026-08-20",
            },
        )
        assert fup_resp.status_code == 201

        # 6. List Follow-ups
        list_fup_resp = client.get("/api/v1/comms/followups")
        assert list_fup_resp.status_code == 200
        assert len(list_fup_resp.json()) >= 1

        # 7. Analyze
        ana_resp = client.post(
            "/api/v1/comms/analyze",
            json={"transcript": "We need to buy 100 enterprise licenses. I will call tomorrow."},
        )
        assert ana_resp.status_code == 200
        assert ana_resp.json()["lead_identified"] is True


def test_communications_acceptance_scenario() -> None:
    """Roadmap Acceptance Test for Phase 16:

    'Send WhatsApp message to +1-415-555-0199 saying "Your demo is confirmed for Friday"
    and schedule follow-up in 3 days.'
    """
    with TestClient(app) as client:
        message = (
            "Send WhatsApp message to +1-415-555-0199 saying 'Your demo is confirmed for Friday' "
            "and schedule follow-up in 3 days."
        )
        resp = client.post("/api/v1/chat/messages", json={"message": message})
        assert resp.status_code == 202
        task_id = resp.json()["id"]

        deadline = time.time() + 10.0
        task: dict[str, object] = {}
        while time.time() < deadline:
            task_resp = client.get(f"/api/v1/tasks/{task_id}")
            assert task_resp.status_code == 200
            task = task_resp.json()
            if task["status"] in {"success", "failed", "cancelled"}:
                break
            time.sleep(0.1)

        assert task["status"] == "success", f"Task failed with error: {task.get('error')}"
        plan = task.get("plan", {})
        assert isinstance(plan, dict)
        steps = plan.get("steps", [])
        assert len(steps) >= 2
        step_caps = [s["capability"] for s in steps]
        assert "comms.whatsapp.send" in step_caps
        assert "comms.followup.schedule" in step_caps

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        evidence_str = " ".join(str(e).lower() for e in evidence)
        assert "whatsapp" in evidence_str
        assert "follow-up" in evidence_str or "scheduled" in evidence_str
