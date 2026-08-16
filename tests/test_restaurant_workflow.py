from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.src.ceo_os_api.main import app
from communications.telephony.manager import CallManager
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.google.client import GoogleClient
from memory.embedding import FeatureHashEmbeddingProvider
from memory.service import MemoryService, initialize_memory_schema
from workflows.restaurant import (
    ReservationRequest,
    RestaurantBookingTool,
    RestaurantBookingWorkflow,
    RestaurantWorkflowIntegration,
)


def test_restaurant_workflow_manifest_and_tool_registration() -> None:
    integration = RestaurantWorkflowIntegration()
    manifest = integration.manifest()

    assert manifest.name == "restaurant_workflow"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.EXTERNAL_COMMUNICATION

    import asyncio

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 1
    assert tools[0].spec.name == "workflow.restaurant.book"
    assert tools[0].spec.risk == RiskLevel.EXTERNAL_COMMUNICATION


@pytest.mark.asyncio
async def test_restaurant_workflow_orchestrator_execution(tmp_path: Path) -> None:
    db_path = tmp_path / "wf_mem.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    await initialize_memory_schema(engine)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedder = FeatureHashEmbeddingProvider()
    memory_service = MemoryService(session_factory, "sqlite", embedder)

    google_client = GoogleClient()
    call_manager = CallManager(memory_service=memory_service)
    workflow = RestaurantBookingWorkflow(
        google_client=google_client,
        call_manager=call_manager,
        memory_service=memory_service,
    )

    req = ReservationRequest(
        restaurant_name="Osteria Bella",
        party_size=4,
        date="2026-08-16",
        time="7:00 PM",
        booking_name="Abdullah",
        location_bias="San Francisco",
    )

    result = await workflow.execute(req)

    # 1. Verify Status & Core Details
    assert result.status == "confirmed"
    assert result.restaurant_name == "Osteria Bella"
    assert result.address == "456 Market St, San Francisco, CA 94105"
    assert result.phone_number == "+1-415-555-7890"
    assert result.party_size == 4
    assert result.booking_name == "Abdullah"

    # 2. Verify Telephony Call & Calendar Event IDs
    assert result.call_id is not None and result.call_id.startswith("call_")
    assert result.calendar_event_id is not None and result.calendar_event_id.startswith("evt_")

    # 3. Verify Episodic Memory was Created
    assert result.memory_id is not None
    memories = await memory_service.search("Osteria Bella", memory_type="episodic")
    assert len(memories) >= 1
    assert "Osteria Bella" in memories[0].content
    assert memories[0].attributes.get("party_size") == 4

    # 4. Verify Full 5-Stage Evidence Trail
    assert len(result.evidence) >= 5
    assert any("1. Places" in e for e in result.evidence)
    assert any("2. Telephony" in e for e in result.evidence)
    assert any("3. Calendar" in e for e in result.evidence)
    assert any("4. Memory" in e for e in result.evidence)
    assert any("5. Report" in e for e in result.evidence)

    await engine.dispose()


@pytest.mark.asyncio
async def test_restaurant_booking_tool_execution() -> None:
    workflow = RestaurantBookingWorkflow()
    tool = RestaurantBookingTool(workflow)

    res = await tool.execute(
        {
            "restaurant_name": "Osteria Bella",
            "party_size": 2,
            "time": "7:00 PM",
            "booking_name": "Ansari",
        }
    )

    assert res.output["status"] == "confirmed"
    assert res.output["restaurant_name"] == "Osteria Bella"
    assert res.output["party_size"] == 2
    assert len(res.evidence) >= 4


def test_api_restaurant_booking_endpoint() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/workflows/restaurant-booking",
            json={
                "restaurant_name": "Osteria Bella",
                "party_size": 4,
                "time": "7:00 PM",
                "booking_name": "Abdullah",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"
        assert data["restaurant_name"] == "Osteria Bella"
        assert data["party_size"] == 4
        assert data["call_id"] is not None
        assert data["calendar_event_id"] is not None
        assert len(data["evidence"]) >= 4


def test_restaurant_booking_full_acceptance() -> None:
    """Roadmap Acceptance Test for Phase 13:

    'Find restaurant → identify number → call → book → calendar → report.
    No manual intervention unless required.'
    """
    with TestClient(app) as client:
        message = (
            "Find restaurant named Osteria Bella, call them to book a table for 4 at "
            "7:00 PM tonight, add to calendar, and report back."
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
        assert len(steps) == 1
        assert steps[0]["capability"] == "workflow.restaurant.book"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        assert len(evidence) >= 4

        # Verify all 5 stages of acceptance are documented in evidence
        assert any("Places" in str(e) for e in evidence)
        assert any("Telephony" in str(e) for e in evidence)
        assert any("Calendar" in str(e) for e in evidence)
        assert any("Report" in str(e) or "booked table" in str(e).lower() for e in evidence)
