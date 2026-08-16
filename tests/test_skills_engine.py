import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.router import CapabilityRouter
from skills.contracts import SkillStep
from skills.engine import SkillsEngine
from skills.integration import SkillsIntegration


def test_skills_manifest_and_tool_registration() -> None:
    integration = SkillsIntegration()
    manifest = integration.manifest()

    assert manifest.name == "skills_engine"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.EXTERNAL_COMMUNICATION

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 7
    tool_names = {t.spec.name for t in tools}
    expected = {
        "skills.create",
        "skills.execute",
        "skills.test",
        "skills.version",
        "skills.disable",
        "skills.list",
        "skills.get",
    }
    assert expected.issubset(tool_names)


def test_skills_engine_builtin_library() -> None:
    engine = SkillsEngine()
    skills = engine.list_skills()
    assert len(skills) >= 4

    report_skill = engine.get_skill("prepare_client_report")
    assert report_skill.category == "reporting"
    assert len(report_skill.steps) == 3
    assert report_skill.steps[0].capability == "business.finance.invoices"
    assert report_skill.steps[2].capability == "comms.email.send"

    meta_skill = engine.get_skill("launch_meta_campaign")
    assert meta_skill.category == "marketing"
    assert len(meta_skill.steps) == 2

    sales_skill = engine.get_skill("analyze_weekly_sales")
    assert sales_skill.category == "sales"
    assert len(sales_skill.steps) == 3

    lead_skill = engine.get_skill("qualify_lead")
    assert lead_skill.category == "sales"
    assert len(lead_skill.steps) == 2


def test_skills_create_get_list() -> None:
    engine = SkillsEngine()
    new_steps = [
        SkillStep(
            step_id="step_1_git",
            capability="shell.run",
            arguments_template={"command": "git pull origin main"},
            success_condition="Repository synchronized",
        ),
        SkillStep(
            step_id="step_2_build",
            capability="shell.run",
            arguments_template={"command": "npm run build"},
            success_condition="Production bundle built",
        ),
    ]

    created = engine.create_skill(
        name="Deploy Web Application",
        description="Pull latest commits and trigger production build.",
        steps=new_steps,
        category="devops",
        tags=["deployment", "ci_cd"],
        owner_agent="developer",
    )

    assert created.name == "Deploy Web Application"
    assert created.version == "1.0.0"
    assert created.skill_id == "deploy_web_application"
    assert len(created.steps) == 2
    assert len(created.version_history) == 1

    fetched = engine.get_skill("deploy_web_application")
    assert fetched.name == created.name

    devops_skills = engine.list_skills(category="devops")
    assert len(devops_skills) == 1
    assert devops_skills[0].skill_id == "deploy_web_application"


def test_skills_dry_run_testing_simulation() -> None:
    engine = SkillsEngine()

    # 1. Valid test
    test_res = engine.test_skill(
        skill_id="prepare_client_report",
        mock_inputs={
            "client_name": "Apex Corp",
            "recipient_email": "billing@apex.com",
            "subject": "Monthly Retainer Report",
        },
    )
    assert test_res.passed is True
    assert len(test_res.validation_errors) == 0
    assert len(test_res.step_results) == 3
    assert test_res.simulated_duration_ms >= 0

    # 2. Missing required parameter test
    failing_test = engine.test_skill(
        skill_id="prepare_client_report",
        mock_inputs={"client_name": "Incomplete Input"},
    )
    assert failing_test.passed is False
    assert len(failing_test.validation_errors) >= 1
    assert "recipient_email" in failing_test.validation_errors[0]


@pytest.mark.asyncio
async def test_skills_execution_pipeline_and_telemetry() -> None:
    engine = SkillsEngine()
    skill = engine.get_skill("prepare_client_report")
    assert skill.stats.runs_count == 0

    exec_res = await engine.execute_skill(
        skill_id="prepare_client_report",
        inputs={
            "client_name": "Starlight Digital",
            "recipient_email": "ops@starlight.com",
            "subject": "Executive Operations Report",
        },
    )

    assert exec_res.status == "success"
    assert exec_res.steps_executed == 3
    assert exec_res.total_steps == 3
    assert len(exec_res.step_outputs) == 3
    assert len(exec_res.evidence) >= 3
    assert exec_res.duration_ms > 0

    # Verify telemetry stats
    assert skill.stats.runs_count == 1
    assert skill.stats.success_count == 1
    assert skill.stats.failure_count == 0
    assert skill.stats.success_rate == 100.0
    assert skill.stats.last_used_at is not None


def test_skills_versioning_and_changelog() -> None:
    engine = SkillsEngine()
    updated = engine.version_skill(
        skill_id="prepare_client_report",
        new_version="1.1.0",
        changelog="Added automatic currency conversion and invoice attachment.",
        new_description="Updated client report with automated invoice breakdowns.",
    )

    assert updated.version == "1.1.0"
    assert updated.description == "Updated client report with automated invoice breakdowns."
    assert len(updated.version_history) == 1
    assert updated.version_history[0].version == "1.0.0"
    assert "Added automatic currency" in updated.version_history[0].changelog


@pytest.mark.asyncio
async def test_skills_disable_and_enable() -> None:
    engine = SkillsEngine()

    # Disable skill
    disabled = engine.disable_skill("qualify_lead", disabled=True)
    assert disabled.enabled is False

    with pytest.raises(ValueError, match="currently disabled"):
        await engine.execute_skill(
            skill_id="qualify_lead",
            inputs={
                "transcript": "Lead transcript",
                "prospect_name": "Test",
                "prospect_email": "test@test.com",
            },
        )

    # Re-enable skill
    enabled = engine.disable_skill("qualify_lead", disabled=False)
    assert enabled.enabled is True

    res = await engine.execute_skill(
        skill_id="qualify_lead",
        inputs={
            "transcript": "Lead transcript",
            "prospect_name": "Test",
            "prospect_email": "test@test.com",
        },
    )
    assert res.status == "success"


def test_capability_router_skills_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains("Create a reusable skill for monthly reporting")
    assert "integrations" in domains

    exec_domains = router.classify_domains("Execute skill prepare_client_report")
    assert "integrations" in exec_domains

    lib_domains = router.classify_domains("Show all skills in library")
    assert "integrations" in lib_domains


def test_api_skills_endpoints() -> None:
    with TestClient(app) as client:
        # 1. List skills
        list_resp = client.get("/api/v1/skills")
        assert list_resp.status_code == 200
        skills_data = list_resp.json()
        assert len(skills_data) >= 4

        # 2. Create skill
        create_resp = client.post(
            "/api/v1/skills",
            json={
                "name": "Quick Health Check",
                "description": "Checks system info and financial status.",
                "steps": [
                    {
                        "step_id": "step_1",
                        "capability": "system_info.platform",
                        "arguments_template": {},
                        "success_condition": "System info retrieved",
                    }
                ],
                "category": "diagnostics",
            },
        )
        assert create_resp.status_code == 201
        created_skill = create_resp.json()
        assert created_skill["name"] == "Quick Health Check"
        sid = created_skill["skill_id"]

        # 3. Get skill
        get_resp = client.get(f"/api/v1/skills/{sid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["skill_id"] == sid

        # 4. Test skill
        test_resp = client.post(f"/api/v1/skills/{sid}/test", json={"mock_inputs": {}})
        assert test_resp.status_code == 200
        assert test_resp.json()["passed"] is True

        # 5. Execute skill
        exec_resp = client.post(f"/api/v1/skills/{sid}/execute", json={"inputs": {}})
        assert exec_resp.status_code == 200
        assert exec_resp.json()["status"] == "success"

        # 6. Version skill
        ver_resp = client.post(
            f"/api/v1/skills/{sid}/version",
            json={
                "new_version": "1.1.0",
                "changelog": "Upgraded system diagnostics checks.",
            },
        )
        assert ver_resp.status_code == 200
        assert ver_resp.json()["version"] == "1.1.0"

        # 7. Disable skill
        dis_resp = client.post(f"/api/v1/skills/{sid}/disable", json={"disabled": True})
        assert dis_resp.status_code == 200
        assert dis_resp.json()["enabled"] is False


def test_skills_acceptance_scenario() -> None:
    """Roadmap Acceptance Test for Phase 18:

    'Create a skill client_onboarding with 2 steps to send welcome email
    and schedule follow-up, then test it.'
    """
    with TestClient(app) as client:
        message = (
            "Create a skill client_onboarding with 2 steps to send "
            "welcome email and schedule follow-up"
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
        assert steps[0]["capability"] == "skills.create"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        evidence_str = " ".join(str(e).lower() for e in evidence)
        assert "created skill" in evidence_str
        assert "procedural steps" in evidence_str
