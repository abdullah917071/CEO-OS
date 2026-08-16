import asyncio
import time

from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.router import CapabilityRouter
from intelligence.business.contracts import DealStage
from intelligence.business.engine import BusinessExecutiveEngine
from intelligence.business.integration import BusinessIntelligenceIntegration


def test_business_intelligence_manifest_and_tool_registration() -> None:
    integration = BusinessIntelligenceIntegration()
    manifest = integration.manifest()

    assert manifest.name == "business_executive_hub"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.READ

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 8
    tool_names = {t.spec.name for t in tools}
    expected = {
        "business.executive.overview",
        "business.finance.overview",
        "business.finance.affordability",
        "business.finance.invoices",
        "business.sales.pipeline",
        "business.sales.deals",
        "business.operations.health",
        "business.operations.inventory",
    }
    assert expected.issubset(tool_names)

    for tool in tools:
        assert tool.spec.risk == RiskLevel.READ


def test_business_finance_overview_and_runway() -> None:
    engine = BusinessExecutiveEngine()
    fin = engine.get_financial_overview()

    assert fin.cash_balance == 1840000.0
    assert fin.total_revenue_mtd == 1280000.0
    assert fin.net_profit_mtd == 540000.0
    assert fin.receivables_overdue == 235000.0  # 150k + 85k
    assert len(fin.unpaid_invoices) >= 3

    # Check SaaS hosting increase alert
    increased = engine.list_subscriptions(increased_only=True)
    assert len(increased) == 1
    assert increased[0].vendor == "Cloud VPS Cluster"
    assert increased[0].delta_amount == 1200.0

    runway = engine.get_financial_runway()
    assert runway.runway_months >= 8.0


def test_business_finance_affordability_simulation() -> None:
    engine = BusinessExecutiveEngine()

    # 1. Affordable scenario: ₹2 Lakh
    sim = engine.simulate_affordability(proposed_spend=200000.0, purpose="advertising push")
    assert sim.affordability_verdict == "AFFORDABLE"
    assert sim.cash_buffer_remaining == 1640000.0
    assert sim.projected_runway_impact_months > 0
    assert sim.breakeven_units_or_conversions >= 20
    assert "Approved" in sim.recommendation

    # 2. High Risk scenario: ₹15 Lakh
    risky = engine.simulate_affordability(proposed_spend=1500000.0, purpose="massive expansion")
    assert risky.affordability_verdict == "HIGH_RISK"
    assert "Unrecommended" in risky.recommendation


def test_business_sales_pipeline_and_deals() -> None:
    engine = BusinessExecutiveEngine()
    pipeline = engine.get_sales_pipeline()

    assert pipeline.total_deals == 4
    assert pipeline.pipeline_value == 1850000.0
    assert pipeline.weighted_value == 1185000.0
    assert pipeline.won_this_month == 520000.0
    assert pipeline.win_rate == 68.4

    proposals = engine.list_deals(stage=DealStage.PROPOSAL_SENT.value)
    assert len(proposals) == 1
    assert proposals[0].prospect_name == "Apex Logistics"


def test_business_operations_health_and_inventory() -> None:
    engine = BusinessExecutiveEngine()
    health = engine.get_operations_health()

    assert health.total_orders_today == 142
    assert health.fulfillment_rate == 98.6
    assert len(health.open_exceptions) == 2
    assert health.refund_rate_percentage == 1.4

    low_stock = engine.list_inventory(low_stock_only=True)
    assert len(low_stock) == 1
    assert low_stock[0].sku == "sku_box_01"
    assert low_stock[0].status == "LOW_STOCK"


def test_business_executive_overview_synthesis() -> None:
    engine = BusinessExecutiveEngine()
    overview = engine.get_executive_overview(date="2026-08-16")

    assert overview.headline_status == "HEALTHY"
    assert overview.revenue_growth_pct == 11.0
    assert "Google CPA increased 19%" in overview.marketing_summary
    assert "Two clients haven't paid invoices" in overview.finance_summary
    assert "hosting subscription increased by ₹1,200" in overview.finance_summary
    assert "Fulfillment rate at 98.6%" in overview.operations_summary
    assert len(overview.action_items) == 4
    assert "Business is mostly healthy" in overview.summary


def test_capability_router_business_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains("Can we afford another ₹2 lakh advertising push?")
    assert "integrations" in domains

    exec_domains = router.classify_domains("CEO, what's happening?")
    assert "integrations" in exec_domains

    pipe_domains = router.classify_domains("Show sales pipeline and deals")
    assert "integrations" in pipe_domains


def test_api_business_intelligence_endpoints() -> None:
    with TestClient(app) as client:
        # 1. Executive Overview
        overview_resp = client.get("/api/v1/intelligence/business/overview")
        assert overview_resp.status_code == 200
        data = overview_resp.json()
        assert data["headline_status"] == "HEALTHY"
        assert data["revenue_growth_pct"] == 11.0
        assert len(data["unpaid_invoices"]) >= 2

        # 2. Finance Overview
        fin_resp = client.get("/api/v1/intelligence/business/finance")
        assert fin_resp.status_code == 200
        assert fin_resp.json()["cash_balance"] == 1840000.0

        # 3. Affordability Simulation
        afford_resp = client.get(
            "/api/v1/intelligence/business/finance/affordability",
            params={"proposed_spend": 200000.0, "purpose": "advertising push"},
        )
        assert afford_resp.status_code == 200
        assert afford_resp.json()["affordability_verdict"] == "AFFORDABLE"

        # 4. Invoices
        inv_resp = client.get(
            "/api/v1/intelligence/business/finance/invoices",
            params={"status": "OVERDUE"},
        )
        assert inv_resp.status_code == 200
        assert len(inv_resp.json()) == 2

        # 5. Sales Pipeline
        pipe_resp = client.get("/api/v1/intelligence/business/sales/pipeline")
        assert pipe_resp.status_code == 200
        assert pipe_resp.json()["pipeline_value"] == 1850000.0

        # 6. Operations Health
        ops_resp = client.get("/api/v1/intelligence/business/operations/health")
        assert ops_resp.status_code == 200
        assert ops_resp.json()["fulfillment_rate"] == 98.6

        # 7. Inventory
        inv_items_resp = client.get(
            "/api/v1/intelligence/business/operations/inventory",
            params={"low_stock_only": True},
        )
        assert inv_items_resp.status_code == 200
        assert len(inv_items_resp.json()) == 1


def test_business_acceptance_executive_briefing() -> None:
    """Roadmap Acceptance Test 1 for Phase 17:

    'CEO, what's happening?'
    Synthesizes multi-department state (Revenue +11%, Meta good, Google CPA +19%,
    2 overdue invoices, ₹1,200 hosting increase, developer checkout update, call at 3:30).
    """
    with TestClient(app) as client:
        message = "CEO, what's happening?"
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
        assert steps[0]["capability"] == "business.executive.overview"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        evidence_str = " ".join(str(e).lower() for e in evidence)
        assert "executive status" in evidence_str
        assert "revenue growth" in evidence_str or "+11" in evidence_str
        assert "healthy" in evidence_str


def test_business_acceptance_affordability_forecasting() -> None:
    """Roadmap Acceptance Test 2 for Phase 17:

    'Can we afford another ₹2 lakh advertising push?'
    Performs capital allocation simulation and returns runway projection.
    """
    with TestClient(app) as client:
        message = "Can we afford another ₹2 lakh advertising push?"
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
        assert steps[0]["capability"] == "business.finance.affordability"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        evidence_str = " ".join(str(e).lower() for e in evidence)
        assert "affordability verdict" in evidence_str
        assert "affordable" in evidence_str
        assert "approved" in evidence_str
