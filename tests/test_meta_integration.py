from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.meta.client import MetaClient
from integrations.meta.provider import MetaMarketingIntegration
from integrations.router import CapabilityRouter


def test_meta_manifest_and_tool_registration() -> None:
    integration = MetaMarketingIntegration()
    manifest = integration.manifest()

    assert manifest.name == "meta_marketing"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.EXTERNAL_COMMUNICATION

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 13
    tool_names = {t.spec.name for t in tools}
    expected = {
        "meta.accounts.list",
        "meta.accounts.get",
        "meta.campaigns.list",
        "meta.campaigns.create",
        "meta.campaigns.update",
        "meta.adsets.list",
        "meta.adsets.create",
        "meta.creatives.list",
        "meta.creatives.create",
        "meta.ads.list",
        "meta.ads.create",
        "meta.insights.get",
        "meta.reporting.campaign",
    }
    assert expected.issubset(tool_names)


@pytest.mark.asyncio
async def test_meta_client_campaign_lifecycle() -> None:
    client = MetaClient()

    # 1. Accounts
    accounts = await client.list_ad_accounts()
    assert len(accounts) >= 1
    acc = accounts[0]
    assert acc.currency == "INR"

    # 2. Create Campaign
    camp = await client.create_campaign(
        account_id=acc.id,
        name="AI Leadership Series",
        objective="OUTCOME_TRAFFIC",
        status="DRAFT",
        daily_budget=800.0,
    )
    assert camp.id.startswith("cmp_")
    assert camp.status == "DRAFT"
    assert camp.daily_budget == 800.0

    # 3. Create Creative
    cr = await client.create_creative(
        account_id=acc.id,
        name="Hero Banner Creative",
        title="Lead With AI Autonomy",
        body="Scale operations without linear headcount.",
        call_to_action_type="SIGN_UP",
    )
    assert cr.id.startswith("cr_")

    # 4. Create Ad Set
    adset = await client.create_adset(
        campaign_id=camp.id,
        name="Tech CEOs in India",
        targeting={"geo_locations": {"countries": ["IN"]}, "interests": [{"name": "AI"}]},
        daily_budget=800.0,
        status="DRAFT",
    )
    assert adset.id.startswith("adset_")

    # 5. Create Ad
    ad = await client.create_ad(
        adset_id=adset.id,
        name="Hero Ad V1",
        creative_id=cr.id,
        status="DRAFT",
    )
    assert ad.id.startswith("ad_")
    assert ad.status == "DRAFT"

    # 6. Update Campaign
    updated = await client.update_campaign(camp.id, status="ACTIVE", daily_budget=1200.0)
    assert updated.status == "ACTIVE"
    assert updated.daily_budget == 1200.0


@pytest.mark.asyncio
async def test_meta_client_insights_and_reporting() -> None:
    client = MetaClient()
    campaigns = await client.list_campaigns()
    camp_id = campaigns[0].id

    # 1. Fetch Insights
    insights = await client.get_insights(camp_id)
    assert len(insights) >= 1
    ins = insights[0]
    assert ins.spend > 0
    assert ins.impressions > 0
    assert ins.clicks > 0
    assert ins.ctr > 0
    assert ins.roas > 0

    # 2. Executive Report
    report = await client.generate_report(camp_id)
    assert report.campaign_id == camp_id
    assert report.currency == "INR"
    assert "Campaign" in report.summary
    assert report.conversions >= 0


def test_capability_router_meta_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains("Create a draft ₹800/day campaign targeting Founders")
    assert "integrations" in domains

    meta_domains = router.classify_domains("Check Instagram ads performance and ROAS on Meta")
    assert "integrations" in meta_domains


def test_api_meta_endpoints() -> None:
    with TestClient(app) as client:
        # Accounts
        acc_resp = client.get("/api/v1/meta/accounts")
        assert acc_resp.status_code == 200
        accounts = acc_resp.json()
        assert len(accounts) >= 1
        acc_id = accounts[0]["id"]

        # Campaigns
        camp_resp = client.post(
            "/api/v1/meta/campaigns",
            json={
                "account_id": acc_id,
                "name": "API Meta Test Campaign",
                "objective": "OUTCOME_TRAFFIC",
                "status": "DRAFT",
                "daily_budget": 800.0,
            },
        )
        assert camp_resp.status_code == 201
        camp_data = camp_resp.json()
        camp_id = camp_data["id"]
        assert camp_data["daily_budget"] == 800.0

        # Creative
        cr_resp = client.post(
            "/api/v1/meta/creatives",
            json={
                "account_id": acc_id,
                "name": "API Promo Creative",
                "title": "Automate Growth",
                "body": "Next-generation CEO OS for executives.",
            },
        )
        assert cr_resp.status_code == 201
        cr_id = cr_resp.json()["id"]

        # AdSet
        adset_resp = client.post(
            "/api/v1/meta/adsets",
            json={
                "campaign_id": camp_id,
                "name": "Entrepreneurs Target Set",
                "targeting": {"interests": [{"name": "Entrepreneurs"}]},
                "daily_budget": 800.0,
            },
        )
        assert adset_resp.status_code == 201
        adset_id = adset_resp.json()["id"]

        # Ad
        ad_resp = client.post(
            "/api/v1/meta/ads",
            json={
                "adset_id": adset_id,
                "name": "Main Banner Ad",
                "creative_id": cr_id,
            },
        )
        assert ad_resp.status_code == 201

        # Insights & Report
        rep_resp = client.get(f"/api/v1/meta/reports/{camp_id}")
        assert rep_resp.status_code == 200
        assert "Campaign" in rep_resp.json()["summary"]


def test_meta_task_execution_acceptance() -> None:
    """Roadmap Acceptance Test for Phase 14:

    'Create a draft ₹800/day campaign targeting X using creative Y.'
    CEO → Marketing → Meta tool.
    """
    with TestClient(app) as client:
        message = (
            "Create a draft ₹800/day campaign targeting Entrepreneurs using creative Launch Promo."
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
        assert "meta.campaigns.create" in step_caps
        assert "meta.creatives.create" in step_caps

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        assert any("campaign" in str(e).lower() for e in evidence)
        assert any("creative" in str(e).lower() for e in evidence)
