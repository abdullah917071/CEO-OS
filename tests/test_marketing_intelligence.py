from __future__ import annotations

import asyncio
import time

from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.router import CapabilityRouter
from intelligence.marketing.engine import MarketingIntelligenceEngine
from intelligence.marketing.provider import MarketingIntelligenceIntegration


def test_marketing_intelligence_manifest_and_tool_registration() -> None:
    integration = MarketingIntelligenceIntegration()
    manifest = integration.manifest()

    assert manifest.name == "marketing_intelligence"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.READ

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 4
    tool_names = {t.spec.name for t in tools}
    expected = {
        "marketing.profit.diagnose",
        "marketing.attribution.funnel",
        "marketing.creatives.analyze",
        "marketing.snapshot.get",
    }
    assert expected.issubset(tool_names)
    for tool in tools:
        assert tool.spec.risk == RiskLevel.READ


def test_marketing_intelligence_engine_diagnostics() -> None:
    engine = MarketingIntelligenceEngine()
    report = engine.diagnose_profit_change(
        current_date="2026-08-15",
        previous_date="2026-08-14",
    )

    assert report.date == "2026-08-15"
    assert report.compare_date == "2026-08-14"
    assert report.net_profit < 18400.0
    assert report.profit_delta_percentage < 0
    assert len(report.root_causes) >= 2
    assert any("Ad spend increased" in rc for rc in report.root_causes)
    assert any("bounce rate" in rc for rc in report.root_causes)
    assert len(report.creative_fatigue_alerts) >= 1
    assert any("Executive Automation Showcase" in alert for alert in report.creative_fatigue_alerts)
    assert len(report.recommended_actions) >= 2
    assert "Net profit fell" in report.summary


def test_marketing_intelligence_attribution_funnel() -> None:
    engine = MarketingIntelligenceEngine()
    funnel = engine.get_attribution_funnel(date_start="2026-08-01", date_stop="2026-08-15")

    stages = funnel["funnel_stages"]
    assert len(stages) == 7
    stage_names = [s["stage"] for s in stages]
    assert "1. Ad Impressions" in stage_names
    assert "2. Ad Clicks" in stage_names
    assert "3. Site Sessions" in stage_names
    assert "4. Qualified Leads" in stage_names
    assert "5. Paid Orders" in stage_names
    assert "6. Net Revenue" in stage_names
    assert "7. Net Profit" in stage_names

    assert funnel["roas"] > 0
    assert funnel["cac"] > 0
    assert funnel["contribution_margin_pct"] > 0


def test_marketing_intelligence_creative_fatigue() -> None:
    engine = MarketingIntelligenceEngine()
    creatives = engine.analyze_creatives(timeframe="7d")

    assert len(creatives) >= 1
    cr = creatives[0]
    assert cr.creative_id == "cr_738291045"
    assert cr.fatigue_score >= 0.8
    assert cr.status == "fatigued"


def test_capability_router_marketing_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains("Why did profit fall yesterday?")
    assert "integrations" in domains

    funnel_domains = router.classify_domains("Show multi-channel marketing attribution funnel")
    assert "integrations" in funnel_domains

    fatigue_domains = router.classify_domains("Check creative fatigue on Meta and Google")
    assert "integrations" in fatigue_domains


def test_api_marketing_intelligence_endpoints() -> None:
    with TestClient(app) as client:
        # Diagnose
        diag_resp = client.get("/api/v1/intelligence/marketing/diagnose")
        assert diag_resp.status_code == 200
        diag_data = diag_resp.json()
        assert diag_data["date"] == "2026-08-15"
        assert len(diag_data["root_causes"]) >= 2
        assert "Net profit fell" in diag_data["summary"]

        # Snapshot
        snap_resp = client.get("/api/v1/intelligence/marketing/snapshot")
        assert snap_resp.status_code == 200
        snap_data = snap_resp.json()
        assert snap_data["date"] == "2026-08-15"
        assert snap_data["total_spend"] > 0
        assert snap_data["sales"]["net_profit"] > 0

        # Creatives
        cr_resp = client.get("/api/v1/intelligence/marketing/creatives")
        assert cr_resp.status_code == 200
        creatives = cr_resp.json()
        assert len(creatives) >= 1
        assert creatives[0]["status"] == "fatigued"

        # Attribution
        attr_resp = client.get("/api/v1/intelligence/marketing/attribution")
        assert attr_resp.status_code == 200
        attr_data = attr_resp.json()
        assert len(attr_data["funnel_stages"]) == 7


def test_marketing_intelligence_acceptance_scenario() -> None:
    """Roadmap Acceptance Test for Phase 15:

    'Why did profit fall yesterday?'
    CEO correlates Meta, Google, Analytics, CRM, sales, and creatives.
    """
    with TestClient(app) as client:
        message = "Why did profit fall yesterday?"
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
        assert len(steps) >= 1
        assert steps[0]["capability"] == "marketing.profit.diagnose"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        evidence_str = " ".join(str(e).lower() for e in evidence)
        assert "profit" in evidence_str
        assert "root cause" in evidence_str or "diagnosis" in evidence_str
