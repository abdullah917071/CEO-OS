from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.src.ceo_os_api.main import app
from communications.telephony import (
    CallManager,
    CallStatus,
    DeterministicTelephonyProvider,
    TelephonyIntegration,
    TelephonyPolicy,
)
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.router import CapabilityRouter
from memory.embedding import FeatureHashEmbeddingProvider
from memory.service import MemoryService, initialize_memory_schema


def test_telephony_manifest_and_tool_registration() -> None:
    integration = TelephonyIntegration()
    manifest = integration.manifest()

    assert manifest.name == "telephony"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.EXTERNAL_COMMUNICATION
    assert manifest.rate_limits.get("requests_per_minute") == 60

    import asyncio

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 3
    tool_map = {t.spec.name: t for t in tools}

    assert "telephony.call.outbound" in tool_map
    assert tool_map["telephony.call.outbound"].spec.risk == RiskLevel.EXTERNAL_COMMUNICATION

    assert "telephony.call.status" in tool_map
    assert tool_map["telephony.call.status"].spec.risk == RiskLevel.READ

    assert "telephony.call.terminate" in tool_map
    assert tool_map["telephony.call.terminate"].spec.risk == RiskLevel.EXTERNAL_COMMUNICATION


@pytest.mark.asyncio
async def test_deterministic_telephony_opening_hours_dialogue() -> None:
    provider = DeterministicTelephonyProvider()
    record = await provider.initiate_call(
        to_number="+1-415-555-0100",
        from_number="+1-415-555-0199",
        objective="ask whether they're open tomorrow",
    )

    assert record.status == CallStatus.COMPLETED
    assert record.to_number == "+1-415-555-0100"
    assert record.duration_seconds > 0
    assert len(record.turns) >= 4

    # Verify dialogue turns contain realistic speech
    speaker_turns = [t for t in record.turns if t.speaker in ("agent", "party")]
    assert any("open tomorrow" in t.text.lower() for t in speaker_turns)
    assert any("11:00 am" in t.text.lower() for t in speaker_turns)

    # Verify summary and extracted answers
    assert record.summary is not None
    assert record.summary.objective_completed is True
    assert record.extracted_data.get("open_tomorrow") == "Yes"
    assert record.extracted_data.get("opening_time") == "11:00 AM"
    assert record.extracted_data.get("closing_time") == "10:00 PM"


@pytest.mark.asyncio
async def test_deterministic_telephony_reservation_dialogue() -> None:
    provider = DeterministicTelephonyProvider()
    record = await provider.initiate_call(
        to_number="+1-415-555-7890",
        from_number="+1-415-555-0199",
        objective="book table for 4 people at 7 PM",
    )

    assert record.status == CallStatus.COMPLETED
    assert record.summary is not None
    assert record.summary.objective_completed is True
    assert record.extracted_data.get("reservation_status") == "confirmed"
    assert record.extracted_data.get("party_size") == "4"


@pytest.mark.asyncio
async def test_call_manager_lifecycle_and_policy_enforcement() -> None:
    policy = TelephonyPolicy(allowed_prefixes=("+1",), require_e164=True)
    manager = CallManager(policy=policy)

    # Reject non-E.164
    with pytest.raises(ValueError, match="must start with '\\+'"):
        await manager.initiate_call(to_number="4155550100", objective="test")

    # Reject disallowed prefix
    with pytest.raises(ValueError, match="not in allowed prefixes"):
        await manager.initiate_call(to_number="+44-20-7946-0991", objective="test")

    # Valid call
    record = await manager.initiate_call(
        to_number="+1-415-555-0100",
        objective="check business status",
        idempotency_key="idemp_call_test_001",
    )
    assert record.id.startswith("call_")

    # Idempotent call returns identical record
    repeat = await manager.initiate_call(
        to_number="+1-415-555-0100",
        objective="check business status",
        idempotency_key="idemp_call_test_001",
    )
    assert repeat.id == record.id

    # Retrieve call
    fetched = await manager.get_call(record.id)
    assert fetched is not None
    assert fetched.id == record.id

    # List calls
    all_calls = await manager.list_calls()
    assert len(all_calls) >= 1
    assert any(c.id == record.id for c in all_calls)


@pytest.mark.asyncio
async def test_call_manager_episodic_memory_integration(tmp_path: Path) -> None:
    db_path = tmp_path / "telephony_mem.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    await initialize_memory_schema(engine)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedder = FeatureHashEmbeddingProvider()
    memory_service = MemoryService(session_factory, "sqlite", embedder)

    manager = CallManager(memory_service=memory_service)
    record = await manager.initiate_call(
        to_number="+1-415-555-0100",
        objective="ask whether they're open tomorrow",
    )
    assert record.summary is not None

    # Verify episodic memory was persisted
    memories = await memory_service.search("open tomorrow", memory_type="episodic")
    assert len(memories) >= 1
    assert "+1-415-555-0100" in memories[0].content
    assert memories[0].attributes.get("call_id") == record.id
    assert memories[0].provenance[0].source_type == "telephony_call"

    await engine.dispose()


@pytest.mark.asyncio
async def test_telephony_tools_outbound_status_terminate() -> None:
    integration = TelephonyIntegration()
    await integration.connect()
    tools = {t.spec.name: t for t in integration.tools()}

    # 1. Outbound call tool
    outbound = tools["telephony.call.outbound"]
    res = await outbound.execute(
        {
            "to_number": "+1-415-555-0100",
            "objective": "ask whether they're open tomorrow",
        }
    )
    assert res.output["status"] == "completed"
    assert res.output["duration_seconds"] > 0
    assert len(res.output["transcript"]) >= 4
    assert res.evidence
    call_id = res.output["call_id"]

    # 2. Status tool
    status_tool = tools["telephony.call.status"]
    status_res = await status_tool.execute({"call_id": call_id})
    assert status_res.output["call_id"] == call_id
    assert status_res.output["status"] == "completed"

    # 3. Terminate tool
    terminate_tool = tools["telephony.call.terminate"]
    term_res = await terminate_tool.execute({"call_id": call_id})
    assert term_res.output["status"] == "completed"


def test_capability_router_telephony_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains("Please call +14155550100 and check store hours")
    assert "integrations" in domains

    phone_domains = router.classify_domains("Phone the reception to ask questions")
    assert "integrations" in phone_domains


def test_api_telephony_endpoints() -> None:
    with TestClient(app) as client:
        # 1. Initiate outbound call
        init_res = client.post(
            "/api/v1/telephony/calls",
            json={
                "to_number": "+1-415-555-0100",
                "objective": "ask whether they're open tomorrow",
            },
        )
        assert init_res.status_code == 201
        call_data = init_res.json()
        assert call_data["status"] == "completed"
        assert call_data["to_number"] == "+1-415-555-0100"
        assert len(call_data["turns"]) >= 4
        assert call_data["summary"] is not None
        call_id = call_data["id"]

        # 2. List calls
        list_res = client.get("/api/v1/telephony/calls")
        assert list_res.status_code == 200
        calls_list = list_res.json()
        assert any(c["id"] == call_id for c in calls_list)

        # 3. Get call by ID
        get_res = client.get(f"/api/v1/telephony/calls/{call_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == call_id

        # 4. Terminate call
        term_res = client.post(f"/api/v1/telephony/calls/{call_id}/terminate")
        assert term_res.status_code == 200


def test_telephony_task_execution_acceptance() -> None:
    """Roadmap Acceptance Test for Phase 12:

    'Call a test number and ask whether they're open tomorrow.'
    CEO OS plans and executes outbound telephone call, conducts conversation,
    and returns structured evidence and outcomes.
    """
    with TestClient(app) as client:
        message = "Call +1-415-555-0100 and ask whether they're open tomorrow."
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
        assert len(steps) == 1
        assert steps[0]["capability"] == "telephony.call.outbound"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        assert len(evidence) >= 1
        assert any("+1-415-555-0100" in str(e) for e in evidence)
        assert any(
            "open tomorrow" in str(e).lower() or "11:00 am" in str(e).lower() for e in evidence
        )
