"""Unit and integration tests for Garry Tan's gstack virtual engineering suite in CEO OS."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.ceo_os_api.main import app
from apps.api.src.ceo_os_api.planner import DeterministicProvider
from gstack.engine import GstackEngine
from gstack.integration import GstackIntegration
from gstack.tools import (
    GstackCeoReviewTool,
    GstackEngReviewTool,
    GstackOfficeHoursTool,
    GstackPipelineRunTool,
    GstackQaBrowserTool,
    GstackReleaseShipTool,
    GstackStaffReviewTool,
)
from integrations.router import CapabilityRouter


@pytest.mark.asyncio
async def test_gstack_engine_individual_roles() -> None:
    engine = GstackEngine()

    # 1. Think: Office Hours
    oh = engine.run_office_hours("Autonomous AI Executive Agent for Startups")
    assert oh.verdict == "APPROVED_TO_PLAN"
    assert len(oh.forcing_questions) >= 3
    assert len(oh.key_assumptions) >= 2
    assert "10-star" in oh.ten_star_experience or "100%" in oh.ten_star_experience

    # 2. Plan: CEO Review
    ceo = engine.run_ceo_review("Autonomous AI Executive Agent")
    assert ceo.verdict == "PROCEED_WITH_FOCUSED_SCOPE"
    assert len(ceo.scope_cuts) >= 1
    assert bool(ceo.killer_feature)

    # 3. Plan: Eng Review
    eng = engine.run_eng_review("Event-driven agent runtime with PostgreSQL and Redis")
    assert eng.verdict == "ARCHITECTURE_APPROVED"
    assert len(eng.architectural_guardrails) >= 3
    assert len(eng.concurrency_risks) >= 1

    # 4. Plan: Design Review
    des = engine.run_design_review("Cybernetic Obsidian Executive Dashboard")
    assert des.verdict == "DESIGN_APPROVED"
    assert des.ux_heuristic_score >= 90
    assert len(des.anti_ai_slop_checks) >= 2

    # 5. Review: Staff Code Review
    staff = engine.run_staff_review(["apps/api/src/ceo_os_api/main.py", "core/runtime.py"])
    assert staff.verdict == "CLEAN_FOR_PRODUCTION"
    assert len(staff.race_conditions) >= 1

    # 6. Test: QA Browser Verification
    qa = await engine.run_qa(routes=["/", "/tasks", "/agents"])
    assert qa.verdict == "QA_VERIFIED"
    assert len(qa.browser_checks) == 3
    assert len(qa.visual_evidence) >= 2

    # 7. Ship: Release Engineer
    ship = engine.run_ship(git_branch="main", pr_title="feat: release autonomous agent")
    assert ship.ship_status == "SHIPPED_SUCCESSFULLY"
    assert len(ship.checks_passed) >= 2


@pytest.mark.asyncio
async def test_gstack_full_pipeline() -> None:
    engine = GstackEngine()
    result = await engine.run_full_pipeline("Build Autonomous FinOps Monitoring Subsystem")

    assert result.status == "COMPLETED"
    assert result.office_hours is not None
    assert result.ceo_review is not None
    assert result.eng_review is not None
    assert result.staff_review is not None
    assert result.qa is not None
    assert result.ship is not None
    assert result.total_duration_ms > 0


@pytest.mark.asyncio
async def test_gstack_tools_and_integration() -> None:
    engine = GstackEngine()
    integration = GstackIntegration(engine=engine)
    manifest = integration.manifest()

    assert manifest.name == "gstack_engine"
    tools = integration.build_tools()
    assert len(tools) == 7

    # Test tool executions
    oh_tool = GstackOfficeHoursTool(engine)
    oh_res = await oh_tool.execute({"idea_or_spec": "Autonomous Cloud Optimizer"})
    assert oh_res.output["verdict"] == "APPROVED_TO_PLAN"

    ceo_tool = GstackCeoReviewTool(engine)
    ceo_res = await ceo_tool.execute({"plan_spec": "Cloud Optimizer Plan"})
    assert ceo_res.output["verdict"] == "PROCEED_WITH_FOCUSED_SCOPE"

    eng_tool = GstackEngReviewTool(engine)
    eng_res = await eng_tool.execute({"arch_spec": "Microservices Arch"})
    assert eng_res.output["verdict"] == "ARCHITECTURE_APPROVED"

    staff_tool = GstackStaffReviewTool(engine)
    staff_res = await staff_tool.execute({"files": ["main.py"]})
    assert staff_res.output["verdict"] == "CLEAN_FOR_PRODUCTION"

    qa_tool = GstackQaBrowserTool(engine)
    qa_res = await qa_tool.execute({"routes": ["/"]})
    assert qa_res.output["verdict"] == "QA_VERIFIED"

    ship_tool = GstackReleaseShipTool(engine)
    ship_res = await ship_tool.execute({"branch": "main", "pr_title": "feat: release"})
    assert ship_res.output["ship_status"] == "SHIPPED_SUCCESSFULLY"

    pipe_tool = GstackPipelineRunTool(engine)
    pipe_res = await pipe_tool.execute({"objective": "Feature Y"})
    assert pipe_res.output["status"] == "COMPLETED"

    # Router domain classification
    router = CapabilityRouter()
    domains = router.classify_domains("Run gstack office hours and staff review")
    assert "integrations" in domains


@pytest.mark.asyncio
async def test_gstack_planner_intents() -> None:
    engine = GstackEngine()
    integration = GstackIntegration(engine=engine)
    tools = integration.build_tools()
    caps = [t.spec for t in tools]

    planner = DeterministicProvider()

    # /office-hours
    plan1 = await planner.plan("/office-hours Build AI Sales Director", caps)
    assert len(plan1.steps) == 1
    assert plan1.steps[0].capability == "gstack.office_hours"

    # /plan-ceo-review
    plan2 = await planner.plan("/plan-ceo-review Launch autonomous email engine", caps)
    assert len(plan2.steps) == 1
    assert plan2.steps[0].capability == "gstack.plan.ceo_review"

    # /plan-eng-review
    plan3 = await planner.plan("/plan-eng-review HNSW vector memory persistence", caps)
    assert len(plan3.steps) == 1
    assert plan3.steps[0].capability == "gstack.plan.eng_review"

    # gstack pipeline
    plan4 = await planner.plan("Run gstack pipeline for customer acquisition engine", caps)
    assert len(plan4.steps) == 1
    assert plan4.steps[0].capability == "gstack.pipeline.run"


@pytest.mark.asyncio
async def test_gstack_fastapi_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Status
        res = await client.get("/api/v1/gstack/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert "gstack" in data["engine"].lower()

        # 2. Office Hours
        res = await client.post(
            "/api/v1/gstack/office-hours",
            json={"idea_or_spec": "Autonomous AI Agent platform"},
        )
        assert res.status_code == 200
        oh_data = res.json()
        assert oh_data["verdict"] == "APPROVED_TO_PLAN"

        # 3. CEO Review
        res = await client.post(
            "/api/v1/gstack/plan/ceo-review",
            json={"plan_spec": "Plan for autonomous workforce"},
        )
        assert res.status_code == 200
        ceo_data = res.json()
        assert ceo_data["verdict"] == "PROCEED_WITH_FOCUSED_SCOPE"

        # 4. Eng Review
        res = await client.post(
            "/api/v1/gstack/plan/eng-review",
            json={"arch_spec": "Architecture for high-speed LLM router"},
        )
        assert res.status_code == 200
        eng_data = res.json()
        assert eng_data["verdict"] == "ARCHITECTURE_APPROVED"

        # 5. Staff Review
        res = await client.post(
            "/api/v1/gstack/review",
            json={"files": ["main.py"]},
        )
        assert res.status_code == 200
        staff_data = res.json()
        assert staff_data["verdict"] == "CLEAN_FOR_PRODUCTION"

        # 6. QA
        res = await client.post(
            "/api/v1/gstack/qa",
            json={"routes": ["/", "/tasks"]},
        )
        assert res.status_code == 200
        qa_data = res.json()
        assert qa_data["verdict"] == "QA_VERIFIED"

        # 7. Ship
        res = await client.post(
            "/api/v1/gstack/ship",
            json={"branch": "main", "pr_title": "feat: gstack release"},
        )
        assert res.status_code == 200
        ship_data = res.json()
        assert ship_data["ship_status"] == "SHIPPED_SUCCESSFULLY"

        # 8. Pipeline
        res = await client.post(
            "/api/v1/gstack/pipeline",
            json={"objective": "Build Autonomous Marketing Engine"},
        )
        assert res.status_code == 200
        pipe_data = res.json()
        assert pipe_data["status"] == "COMPLETED"
        assert pipe_data["office_hours"] is not None
        assert pipe_data["ship"] is not None
