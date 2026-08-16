from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.google import GoogleEcosystemIntegration
from integrations.router import CapabilityRouter
from integrations.secrets import SecretBroker


def test_google_ecosystem_manifest_and_tool_registration() -> None:
    broker = SecretBroker()
    cid_ref = broker.register_secret("google_access_token", "ya29.test_google_token_123")

    integration = GoogleEcosystemIntegration(
        token_ref=cid_ref.credential_id,
        secret_broker=broker,
    )
    manifest = integration.manifest()
    assert manifest.name == "google_ecosystem"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.EXTERNAL_COMMUNICATION
    assert manifest.oauth_profile is not None
    assert manifest.oauth_profile.provider_name == "google"

    # Connect integration
    import asyncio

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 17
    tool_names = {t.spec.name for t in tools}

    # Verify all 7 Google services are present
    assert "google.gmail.search" in tool_names
    assert "google.gmail.read" in tool_names
    assert "google.gmail.draft" in tool_names
    assert "google.gmail.send" in tool_names
    assert "google.calendar.list" in tool_names
    assert "google.calendar.create_event" in tool_names
    assert "google.calendar.update_event" in tool_names
    assert "google.calendar.freebusy" in tool_names
    assert "google.contacts.search" in tool_names
    assert "google.drive.search" in tool_names
    assert "google.drive.read" in tool_names
    assert "google.drive.create" in tool_names
    assert "google.places.search" in tool_names
    assert "google.places.details" in tool_names
    assert "google.analytics.report" in tool_names
    assert "google.youtube.search" in tool_names
    assert "google.youtube.metrics" in tool_names

    # Check risk levels
    gmail_send = next(t for t in tools if t.spec.name == "google.gmail.send")
    assert gmail_send.spec.risk == RiskLevel.EXTERNAL_COMMUNICATION
    gmail_read = next(t for t in tools if t.spec.name == "google.gmail.read")
    assert gmail_read.spec.risk == RiskLevel.READ
    drive_create = next(t for t in tools if t.spec.name == "google.drive.create")
    assert drive_create.spec.risk == RiskLevel.HARMLESS_WRITE


@pytest.mark.asyncio
async def test_gmail_tools_search_read_draft_send() -> None:
    integration = GoogleEcosystemIntegration()
    await integration.connect()
    tools = {t.spec.name: t for t in integration.tools()}

    # 1. Search emails
    search_tool = tools["google.gmail.search"]
    search_res = await search_tool.execute({"query": "budget", "max_results": 5})
    assert len(search_res.output["messages"]) >= 1
    assert "Budget" in search_res.output["messages"][0]["subject"]
    assert len(search_res.evidence) == 1

    # 2. Read specific email
    read_tool = tools["google.gmail.read"]
    msg_id = search_res.output["messages"][0]["id"]
    read_res = await read_tool.execute({"message_id": msg_id})
    assert read_res.output["id"] == msg_id
    assert "Sarah" in read_res.output["body"]

    # 3. Create draft
    draft_tool = tools["google.gmail.draft"]
    draft_res = await draft_tool.execute(
        {
            "recipient": "investor@sequoia.com",
            "subject": "Re: Founders Roundtable RSVP",
            "body": "I will be attending the dinner. Thanks!",
        }
    )
    assert draft_res.output["draft_id"].startswith("draft_")
    assert draft_res.output["recipient"] == "investor@sequoia.com"

    # 4. Send email
    send_tool = tools["google.gmail.send"]
    send_res = await send_tool.execute(
        {
            "recipient": "partner@acme.com",
            "subject": "Contract signed",
            "body": "The signed agreement is attached.",
        },
        idempotency_key="gmail-send-test-01",
    )
    assert send_res.output["status"] == "sent"
    assert send_res.output["message_id"].startswith("msg_")


@pytest.mark.asyncio
async def test_calendar_tools_list_create_update_freebusy() -> None:
    integration = GoogleEcosystemIntegration()
    await integration.connect()
    tools = {t.spec.name: t for t in integration.tools()}

    # 1. List events
    list_tool = tools["google.calendar.list"]
    list_res = await list_tool.execute({"max_results": 5})
    assert len(list_res.output["events"]) >= 1
    assert "Sync" in list_res.output["events"][0]["summary"]

    # 2. Create event
    create_tool = tools["google.calendar.create_event"]
    create_res = await create_tool.execute(
        {
            "summary": "Board Meeting Q3",
            "start_time": "2026-08-20T10:00:00Z",
            "end_time": "2026-08-20T11:30:00Z",
            "location": "Boardroom A",
            "attendees": ["board@company.com"],
        }
    )
    event_id = create_res.output["id"]
    assert event_id.startswith("evt_")
    assert create_res.output["summary"] == "Board Meeting Q3"

    # 3. Update event
    update_tool = tools["google.calendar.update_event"]
    update_res = await update_tool.execute(
        {
            "event_id": event_id,
            "summary": "Board Meeting Q3 (Updated Time)",
            "start_time": "2026-08-20T11:00:00Z",
        }
    )
    assert update_res.output["summary"] == "Board Meeting Q3 (Updated Time)"

    # 4. Check free/busy
    fb_tool = tools["google.calendar.freebusy"]
    fb_res = await fb_tool.execute(
        {"time_min": "2026-08-16T00:00:00Z", "time_max": "2026-08-16T23:59:59Z"}
    )
    assert len(fb_res.output["busy_slots"]) >= 1


@pytest.mark.asyncio
async def test_contacts_drive_places_analytics_youtube_tools() -> None:
    integration = GoogleEcosystemIntegration()
    await integration.connect()
    tools = {t.spec.name: t for t in integration.tools()}

    # Contacts
    contacts_tool = tools["google.contacts.search"]
    c_res = await contacts_tool.execute({"query": "Sarah"})
    assert len(c_res.output["contacts"]) >= 1
    assert "Sarah Jenkins" in c_res.output["contacts"][0]["name"]

    # Drive Search & Create
    drive_search = tools["google.drive.search"]
    ds_res = await drive_search.execute({"query": "Financial"})
    assert len(ds_res.output["files"]) >= 1
    assert "Financial" in ds_res.output["files"][0]["name"]

    drive_read = tools["google.drive.read"]
    dr_res = await drive_read.execute({"file_id": ds_res.output["files"][0]["id"]})
    assert "Revenue" in dr_res.output["content"]

    drive_create = tools["google.drive.create"]
    dc_res = await drive_create.execute(
        {
            "name": "Meeting_Notes.txt",
            "content": "Discussed roadmap and milestones.",
        }
    )
    assert dc_res.output["name"] == "Meeting_Notes.txt"
    assert dc_res.output["id"].startswith("file_")

    # Places / Maps
    places_search = tools["google.places.search"]
    ps_res = await places_search.execute({"query": "Osteria Bella", "location_bias": "SF"})
    assert len(ps_res.output["places"]) >= 1
    assert "Osteria Bella" in ps_res.output["places"][0]["name"]

    places_details = tools["google.places.details"]
    pd_res = await places_details.execute({"place_id": ps_res.output["places"][0]["place_id"]})
    assert pd_res.output["phone_number"] == "+1-415-555-7890"

    # Analytics Report
    analytics_tool = tools["google.analytics.report"]
    ga_res = await analytics_tool.execute({})
    assert ga_res.output["metrics"]["active_users"] > 0
    assert ga_res.output["metrics"]["conversions"] > 0

    # YouTube Search & Metrics
    yt_search = tools["google.youtube.search"]
    yt_res = await yt_search.execute({"query": "AI agents"})
    assert len(yt_res.output["videos"]) >= 1

    yt_metrics = tools["google.youtube.metrics"]
    ytm_res = await yt_metrics.execute({})
    assert ytm_res.output["subscriber_count"] >= 1000


def test_capability_router_google_domains() -> None:
    router = CapabilityRouter()
    assert "integrations" in router.classify_domains("Search emails from investor")
    assert "integrations" in router.classify_domains("Check my calendar for tomorrow")
    assert "integrations" in router.classify_domains("Find Italian restaurant near downtown")
    assert "files" in router.classify_domains("Read Google Drive financial spreadsheet")
    assert "integrations" in router.classify_domains("Query GA4 analytics traffic")
    assert "integrations" in router.classify_domains("Check YouTube channel views")


def test_api_google_ecosystem_capabilities_discovery() -> None:
    with TestClient(app) as client:
        # Check all capabilities
        resp = client.get("/api/v1/capabilities")
        assert resp.status_code == 200
        specs = resp.json()
        names = {s["name"] for s in specs}

        assert "google.gmail.search" in names
        assert "google.gmail.send" in names
        assert "google.calendar.list" in names
        assert "google.contacts.search" in names
        assert "google.drive.search" in names
        assert "google.places.search" in names
        assert "google.analytics.report" in names
        assert "google.youtube.search" in names

        # Check integration list status
        integ_resp = client.get("/api/v1/integrations")
        assert integ_resp.status_code == 200
        google_integ = next((i for i in integ_resp.json() if i["name"] == "google_ecosystem"), None)
        assert google_integ is not None
        assert google_integ["health"] == "healthy"
        assert google_integ["tool_count"] == 17


def test_google_ecosystem_task_execution_acceptance() -> None:
    """Roadmap acceptance scenario for Phase 11 Google Ecosystem."""
    with TestClient(app) as client:
        # 1. Submit email search task to CEO
        chat_resp = client.post(
            "/api/v1/chat/messages",
            json={"message": "Check my emails about budget"},
        )
        assert chat_resp.status_code == 202
        task_id = chat_resp.json()["id"]

        for _ in range(100):
            task = client.get(f"/api/v1/tasks/{task_id}").json()
            if task["status"] in {"success", "failed"}:
                break

        assert task["status"] == "success"
        assert len(task["plan"]["steps"]) >= 1
        assert task["plan"]["steps"][0]["capability"] == "google.gmail.search"
        assert len(task["result"]["evidence"]) >= 1
        assert "Gmail" in task["result"]["evidence"][0]

        # 2. Submit place search task to CEO
        place_resp = client.post(
            "/api/v1/chat/messages",
            json={"message": "Find restaurant named Osteria Bella"},
        )
        assert place_resp.status_code == 202
        place_task_id = place_resp.json()["id"]

        for _ in range(100):
            ptask = client.get(f"/api/v1/tasks/{place_task_id}").json()
            if ptask["status"] in {"success", "failed"}:
                break

        assert ptask["status"] == "success"
        assert len(ptask["plan"]["steps"]) >= 1
        assert ptask["plan"]["steps"][0]["capability"] == "google.places.search"
        assert len(ptask["result"]["evidence"]) >= 1
        assert "Places" in ptask["result"]["evidence"][0]
