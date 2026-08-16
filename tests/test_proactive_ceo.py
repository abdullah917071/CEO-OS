import asyncio
import time

from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.router import CapabilityRouter
from proactive.contracts import TriggerCategory, TriggerSeverity
from proactive.engine import ProactiveCeoEngine
from proactive.integration import ProactiveIntegration


def test_proactive_manifest_and_tool_registration() -> None:
    integration = ProactiveIntegration()
    manifest = integration.manifest()

    assert manifest.name == "proactive_ceo"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.domain == "intelligence"
    assert manifest.risk_ceiling == RiskLevel.HARMLESS_WRITE

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 6
    tool_names = {t.spec.name for t in tools}
    expected = {
        "proactive.evaluate",
        "proactive.insights.get",
        "proactive.trigger.create",
        "proactive.trigger.list",
        "proactive.goal.create",
        "proactive.goal.list",
    }
    assert tool_names == expected


def test_proactive_engine_builtin_triggers_and_goals() -> None:
    engine = ProactiveCeoEngine()
    triggers = engine.list_triggers()
    assert len(triggers) >= 5

    trg_ids = {t.id for t in triggers}
    assert "trg_low_runway" in trg_ids
    assert "trg_overdue_invoices" in trg_ids
    assert "trg_meta_cpa_fatigue" in trg_ids
    assert "trg_fulfillment_exceptions" in trg_ids
    assert "trg_pipeline_stagnation" in trg_ids

    goals = engine.list_goals()
    assert len(goals) >= 3
    goal_ids = {g.id for g in goals}
    assert "goal_revenue_expansion_q4" in goal_ids
    assert "goal_meta_roas_scale" in goal_ids
    assert "goal_recover_receivables" in goal_ids


def test_proactive_trigger_creation_and_custom_evaluation() -> None:
    engine = ProactiveCeoEngine()
    custom_trg = engine.create_trigger(
        name="High Server Latency Alert",
        description="Triggered when API response latency exceeds 500ms.",
        category=TriggerCategory.SYSTEM,
        metric_key="p99_latency_ms",
        operator=">",
        threshold=500.0,
        severity=TriggerSeverity.CRITICAL,
    )
    assert custom_trg.id.startswith("trg_")
    assert custom_trg.condition.metric_key == "p99_latency_ms"

    # Evaluation with latency below threshold -> should not fire custom trigger
    report1 = engine.evaluate_business_state({"p99_latency_ms": 320.0})
    assert not any(i.trigger_id == custom_trg.id for i in report1.insights)

    # Evaluation with latency above threshold -> fires custom trigger
    report2 = engine.evaluate_business_state({"p99_latency_ms": 680.0})
    fired_custom = [i for i in report2.insights if i.trigger_id == custom_trg.id]
    assert len(fired_custom) == 1
    assert fired_custom[0].severity == TriggerSeverity.CRITICAL


def test_proactive_goal_creation_and_progress_tracking() -> None:
    engine = ProactiveCeoEngine()
    goal = engine.create_goal(
        title="Hire 3 Senior Engineers",
        description="Scale core platform engineering team for Q3.",
        category=TriggerCategory.OPERATIONS,
        target_date="2026-09-30",
        milestones=[
            {
                "title": "Hire 1 Backend Lead",
                "target_value": 1.0,
                "current_value": 1.0,
                "unit": "hires",
                "target_date": "2026-08-31",
                "completed": True,
            },
            {
                "title": "Hire 2 AI Engineers",
                "target_value": 2.0,
                "current_value": 0.0,
                "unit": "hires",
                "target_date": "2026-09-30",
                "completed": False,
            },
        ],
    )

    assert goal.id.startswith("goal_")
    assert goal.title == "Hire 3 Senior Engineers"
    assert len(goal.milestones) == 2
    assert goal.milestones[0].completed is True


def test_proactive_insights_synthesizer_and_auto_action_recommendations() -> None:
    engine = ProactiveCeoEngine()
    # Trigger condition: overdue invoices > 0, meta CPA increase > 15%
    report = engine.evaluate_business_state(
        {
            "overdue_invoices_count": 3.0,
            "overdue_amount_inr": 125000.0,
            "meta_cpa_pct_change": 22.4,
        }
    )

    assert report.triggers_fired_count >= 2
    insights_by_title = {i.title: i for i in report.insights}

    # Verify structured proactive format ("You don't need to do anything right now, but I found X")
    inv_insight = insights_by_title.get("Overdue Client Invoices Identified")
    assert inv_insight is not None
    assert "You don't need to do anything right now, but" in inv_insight.observation
    assert "₹125,000.00" in inv_insight.observation
    assert inv_insight.auto_action_capability == "comms.followup.schedule"

    cpa_insight = insights_by_title.get("Meta Ad CPA Fatigue Detected")
    assert cpa_insight is not None
    assert "22.4%" in cpa_insight.observation
    assert cpa_insight.auto_action_capability == "marketing.intelligence.creative_fatigue"


def test_capability_router_proactive_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains(
        "CEO, evaluate all business event triggers and give proactive recommendations"
    )
    assert "integrations" in domains

    goal_domains = router.classify_domains("Track progress on strategic revenue goals")
    assert "integrations" in goal_domains


def test_api_proactive_endpoints() -> None:
    with TestClient(app) as client:
        # 1. List triggers
        trg_resp = client.get("/api/v1/proactive/triggers")
        assert trg_resp.status_code == 200
        triggers = trg_resp.json()
        assert len(triggers) >= 5

        # 2. Create custom trigger
        new_trg_payload = {
            "name": "Refund Rate Spike Warning",
            "description": "Triggered when refund requests exceed 5% of orders.",
            "category": "operations",
            "metric_key": "refund_rate_pct",
            "operator": ">",
            "threshold": 5.0,
            "severity": "warning",
            "enabled": True,
        }
        create_resp = client.post("/api/v1/proactive/triggers", json=new_trg_payload)
        assert create_resp.status_code == 201
        created_trg = create_resp.json()
        assert created_trg["name"] == "Refund Rate Spike Warning"

        # 3. List goals
        goals_resp = client.get("/api/v1/proactive/goals")
        assert goals_resp.status_code == 200
        goals = goals_resp.json()
        assert len(goals) >= 3

        # 4. Create custom goal
        new_goal_payload = {
            "title": "Achieve 99.9% Order SLA",
            "description": "Deliver 99.9% of orders within promised turnaround.",
            "category": "operations",
            "target_date": "2026-11-30",
            "milestones": [
                {
                    "title": "Hit 99.0% SLA",
                    "target_value": 99.0,
                    "current_value": 97.5,
                    "unit": "%",
                    "target_date": "2026-09-30",
                    "completed": False,
                }
            ],
        }
        goal_create_resp = client.post("/api/v1/proactive/goals", json=new_goal_payload)
        assert goal_create_resp.status_code == 201
        created_goal = goal_create_resp.json()
        assert created_goal["title"] == "Achieve 99.9% Order SLA"

        # 5. Evaluate state
        eval_resp = client.post(
            "/api/v1/proactive/evaluate",
            json={"overdue_invoices_count": 2.0, "refund_rate_pct": 6.2},
        )
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert eval_data["triggers_fired_count"] >= 1
        assert len(eval_data["insights"]) >= 1

        # 6. Get proactive insights
        insights_resp = client.get("/api/v1/proactive/insights")
        assert insights_resp.status_code == 200
        insights = insights_resp.json()
        assert len(insights) >= 1


def test_proactive_ceo_acceptance_scenario() -> None:
    """Roadmap Acceptance Test for Phase 20:

    'CEO, evaluate all business event triggers and show proactive insights and recommendations.'
    """
    with TestClient(app) as client:
        message = (
            "CEO, evaluate all business event triggers and "
            "show proactive insights and recommendations"
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
        assert len(steps) >= 1
        assert steps[0]["capability"] == "proactive.evaluate"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        evidence_str = " ".join(str(e).lower() for e in evidence)
        assert "evaluated" in evidence_str
        assert "triggers" in evidence_str
