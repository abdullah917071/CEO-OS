from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agency.catalog import AgencyCatalog
from agency.contracts import AgencyDomain
from agency.engine import AgencyAgentsEngine
from agency.matcher import AgencySkillMatcher
from agency.tools import (
    AgencyAgentSpawnTool,
    AgencySkillsGetTool,
    AgencySkillsListTool,
    AgencySkillsMatchTool,
    AgencyTaskExecuteTool,
)
from agents.templates import AgentTemplateRegistry
from apps.api.src.ceo_os_api.main import app
from core.contracts import RiskLevel
from integrations.router import CapabilityRouter


def test_agency_catalog_loading_and_domain_classification() -> None:
    catalog = AgencyCatalog()
    total_count = catalog.count()
    assert total_count >= 200, f"Expected at least 200 agency skills, found {total_count}"

    # Verify key skills exist
    finops = catalog.get("agency-finops-engineer")
    assert finops is not None
    assert finops.name == "agency-finops-engineer"
    assert finops.domain == AgencyDomain.FINOPS_FINANCE
    assert len(finops.critical_rules) >= 1

    orchestrator = catalog.get("agency-agents-orchestrator")
    assert orchestrator is not None
    assert orchestrator.domain == AgencyDomain.OPERATIONS_PM

    appsec = catalog.get("agency-application-security-engineer")
    assert appsec is not None
    assert appsec.domain == AgencyDomain.SECURITY_QA

    # Domain filtering
    eng_skills = catalog.list(domain=AgencyDomain.ENGINEERING)
    assert len(eng_skills) > 10

    # Search
    search_results = catalog.search("marketing")
    assert len(search_results) >= 1


def test_agency_skill_matcher_accuracy() -> None:
    catalog = AgencyCatalog()
    matcher = AgencySkillMatcher(catalog)

    # 1. AWS and cloud cost query
    res_finops = matcher.match("Audit our AWS spend and unit economics to find cost optimizations")
    assert res_finops.best_match is not None
    assert res_finops.best_match.skill_name == "agency-finops-engineer"
    assert res_finops.best_match.domain == AgencyDomain.FINOPS_FINANCE
    assert res_finops.best_match.relevance_score >= 0.70

    # 2. Meta advertising query
    res_ads = matcher.match(
        "Design RSA copy, asset group, and creative testing framework for Meta ads"
    )
    assert res_ads.best_match is not None
    assert (
        "creative" in res_ads.best_match.skill_name
        or "growth" in res_ads.best_match.skill_name
        or "ad" in res_ads.best_match.skill_name
    )

    # 3. B2B deal qualification
    res_deal = matcher.match("Qualify enterprise pipeline deal using MEDDPICC sales methodology")
    assert res_deal.best_match is not None
    assert res_deal.best_match.skill_name in {
        "agency-deal-strategist",
        "agency-sales-coach",
        "agency-sales-engineer",
    }

    # 4. AppSec threat modeling
    res_sec = matcher.match("Perform appsec threat model and review secure code practices")
    assert res_sec.best_match is not None
    assert res_sec.best_match.domain == AgencyDomain.SECURITY_QA


def test_agency_engine_template_synthesis_and_registration() -> None:
    catalog = AgencyCatalog()
    engine = AgencyAgentsEngine(catalog)
    registry = AgentTemplateRegistry()

    initial_count = len(registry.list())
    registered = engine.register_all_templates(registry)
    assert registered >= 200
    assert len(registry.list()) >= initial_count + 200

    # Verify synthesized template properties
    finops_tmpl = registry.get("agency-finops-engineer")
    assert finops_tmpl.name == "agency-finops-engineer"
    assert "finops" in finops_tmpl.role.lower()
    assert finops_tmpl.budget.max_runtime_seconds == 1800


def test_agency_engine_plan_and_execution() -> None:
    engine = AgencyAgentsEngine()
    plan = engine.plan_execution_with_skill(
        task_id="t_101",
        objective="Analyze current AWS cloud costs and optimize database spend",
    )
    assert plan.matched_skill.name == "agency-finops-engineer"
    assert len(plan.quality_gates) >= 3
    assert "finops" in plan.guidance_prompt.lower()

    result = engine.execute_with_skill(
        task_id="t_101",
        objective="Analyze current AWS cloud costs and optimize database spend",
    )
    assert result.status == "SUCCESS"
    assert result.skill_name == "agency-finops-engineer"
    assert len(result.evidence) >= 3
    assert len(result.quality_checks_passed) >= 3


@pytest.mark.asyncio
async def test_agency_tools_execution() -> None:
    engine = AgencyAgentsEngine()

    # 1. agency.skills.list
    list_tool = AgencySkillsListTool(engine)
    res_list = await list_tool.execute({"domain": "finops_finance"})
    assert res_list.output["count"] >= 5
    assert len(res_list.evidence) >= 1

    # 2. agency.skills.get
    get_tool = AgencySkillsGetTool(engine)
    res_get = await get_tool.execute({"name": "agency-finops-engineer"})
    assert res_get.output["name"] == "agency-finops-engineer"
    assert res_get.output["domain"] == "finops_finance"

    # 3. agency.skills.match
    match_tool = AgencySkillsMatchTool(engine)
    res_match = await match_tool.execute({"query": "Review pull request and refactor rust backend"})
    assert len(res_match.output["matches"]) >= 1

    # 4. agency.agent.spawn
    spawn_tool = AgencyAgentSpawnTool(engine)
    res_spawn = await spawn_tool.execute({"skill_name": "agency-senior-developer"})
    assert res_spawn.output["template_name"] == "agency-senior-developer"

    # 5. agency.task.execute
    exec_tool = AgencyTaskExecuteTool(engine)
    res_exec = await exec_tool.execute(
        {
            "task_id": "t_202",
            "objective": "Audit our security posture and threat detection pipeline",
        }
    )
    assert res_exec.output["status"] == "SUCCESS"
    assert res_exec.output["output"]["domain"] == "security_qa"


def test_capability_router_agency_domain() -> None:
    router = CapabilityRouter()
    spec = AgencySkillsMatchTool(AgencyAgentsEngine()).spec

    assert spec.name == "agency.skills.match"
    assert spec.risk == RiskLevel.READ
    assert router.domain_for_capability(spec) == "integrations"


def test_api_agency_endpoints() -> None:
    with TestClient(app) as client:
        # GET /api/v1/agency/skills
        resp_list = client.get("/api/v1/agency/skills?domain=finops_finance")
        assert resp_list.status_code == 200
        list_data = resp_list.json()
        assert list_data["count"] >= 5

        # GET /api/v1/agency/skills/{skill_name}
        resp_get = client.get("/api/v1/agency/skills/agency-finops-engineer")
        assert resp_get.status_code == 200
        get_data = resp_get.json()
        assert get_data["name"] == "agency-finops-engineer"
        assert get_data["domain"] == "finops_finance"

        # POST /api/v1/agency/match
        resp_match = client.post(
            "/api/v1/agency/match",
            json={
                "query": "Audit cloud AWS costs and unit economics",
                "top_k": 3,
            },
        )
        assert resp_match.status_code == 200
        match_data = resp_match.json()
        assert match_data["best_match"]["skill_name"] == "agency-finops-engineer"

        # POST /api/v1/agency/spawn
        resp_spawn = client.post(
            "/api/v1/agency/spawn",
            json={
                "skill_name": "agency-finops-engineer",
            },
        )
        assert resp_spawn.status_code == 200
        spawn_data = resp_spawn.json()
        assert spawn_data["template_name"] == "agency-finops-engineer"

        # POST /api/v1/agency/execute
        resp_exec = client.post(
            "/api/v1/agency/execute",
            json={
                "task_id": "t_api_99",
                "objective": "Audit our AWS spend and unit economics",
            },
        )
        assert resp_exec.status_code == 200
        exec_data = resp_exec.json()
        assert exec_data["status"] == "SUCCESS"
        assert exec_data["skill_name"] == "agency-finops-engineer"


def test_agency_task_execution_acceptance() -> None:
    """Roadmap Acceptance: CEO matches and executes tasks with relevant agency skills."""
    with TestClient(app) as client:
        message = "CEO, match agency skill for auditing our AWS cloud spend and unit economics"
        resp = client.post("/api/v1/chat/messages", json={"message": message})
        assert resp.status_code == 202
        task_id = resp.json()["id"]

        deadline = time.time() + 10.0
        task: dict[str, Any] = {}
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

        capabilities_executed = [s["capability"] for s in steps]
        assert "agency.skills.match" in capabilities_executed

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        assert len(evidence) >= 1
