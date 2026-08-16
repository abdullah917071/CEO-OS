"""Comprehensive test suite for Universal Agent Registry, Dynamic Router, and Team Orchestration."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agents.registry import (
    AgentDivision,
    AgentProviderSource,
    AgentRouter,
    GeneratedAgentProvider,
    NativeAgentProvider,
    TeamPlan,
    UniversalAgentRegistry,
)
from agents.runtime import (
    TeamOrchestrator,
)
from agents.tools import (
    AgentCreateTool,
    AgentDelegateTool,
    AgentInspectTool,
    AgentSearchTool,
    AgentSpawnTeamTool,
    AgentSpawnTool,
    get_global_agent_registry,
)
from apps.api.src.ceo_os_api.main import app

# ── 1. Registry & Providers ───────────────────────────────────────────────────


def test_native_directors_provider() -> None:
    native = NativeAgentProvider()
    agents = native._agents
    assert len(agents) == 7
    assert "ceo" in agents
    assert "marketing-director" in agents
    assert "developer-director" in agents
    assert "finance-director" in agents
    assert "operations-director" in agents
    assert "research-director" in agents
    assert "communications-director" in agents

    ceo = agents["ceo"]
    assert ceo.is_permanent is True
    assert ceo.division == AgentDivision.GENERAL


@pytest.mark.asyncio
async def test_universal_agent_registry_aggregation() -> None:
    registry = UniversalAgentRegistry()
    all_agents = await registry.list_all_agents()
    assert len(all_agents) >= 200, f"Expected at least 200 agents, found {len(all_agents)}"

    # Check Native directors exist
    ceo = await registry.get_agent("ceo")
    assert ceo is not None
    assert ceo.role == "Chief Executive Officer"

    # Check Agency specialists exist
    finops = await registry.get_agent("agency-finops-engineer")
    assert finops is not None
    assert finops.division == AgentDivision.FINANCE

    # Check search with semantic ranking
    matches = await registry.search(
        "Audit AWS cloud spend and reduce infrastructure costs", limit=3
    )
    assert len(matches) >= 1
    top = matches[0]
    assert (
        "finops" in top.agent.id.lower()
        or "cost" in top.agent.id.lower()
        or "infrastructure" in top.agent.id.lower()
        or top.agent.division in {AgentDivision.FINANCE, AgentDivision.ENGINEERING}
    )
    assert top.relevance_score >= 0.70


# ── 2. Dynamic Router & Team Assembly ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_router_single_and_team_assembly() -> None:
    registry = UniversalAgentRegistry()
    router = AgentRouter(registry)

    # Single specialist match
    match = await router.route_single("Design RSA copy and creative testing framework for Meta ads")
    assert match is not None
    assert match.agent.division == AgentDivision.MARKETING or "creative" in match.agent.id

    # Dynamic team assembly
    team_plan: TeamPlan = await router.route_team(
        "Build an onboarding flow for our SaaS and optimize checkout conversion",
        max_specialists=4,
    )
    assert team_plan.lead_agent_id != ""
    assert len(team_plan.members) >= 2
    assert len(team_plan.execution_order) >= 2


@pytest.mark.asyncio
async def test_team_orchestration_staged_execution() -> None:
    registry = UniversalAgentRegistry()
    orchestrator = TeamOrchestrator(registry)

    res = await orchestrator.assemble_and_run_team(
        "Launch new SaaS feature with landing page, analytics, and security audit",
        max_specialists=3,
    )
    assert res["status"] == "SUCCESS"
    assert res["team_size"] >= 2
    assert len(res["findings"]) >= 2
    assert len(res["recommendations"]) >= 2
    assert len(res["evidence"]) >= 2
    assert "synthesis" in res


# ── 3. Dynamic On-Demand Specialist Creation ──────────────────────────────────


@pytest.mark.asyncio
async def test_generated_agent_provider_on_demand() -> None:
    registry = UniversalAgentRegistry()
    gen_provider: GeneratedAgentProvider = registry.generated_provider

    new_agent = gen_provider.create_dynamic_agent(
        name="GST Tax Compliance Specialist",
        role="Indian GST & Tax Filing Consultant",
        division=AgentDivision.FINANCE,
        mission="Ensure compliance with Indian GST regulations and automated invoice filing.",
        tools=["business.finance.invoices", "memory.recall"],
    )
    assert new_agent.id == "generated-gst-tax-compliance-specialist"
    assert new_agent.source == AgentProviderSource.GENERATED

    retrieved = await registry.get_agent("generated-gst-tax-compliance-specialist")
    assert retrieved is not None
    assert retrieved.name == "GST Tax Compliance Specialist"


# ── 4. Agent Scoring and Historical Outcomes ─────────────────────────────────


@pytest.mark.asyncio
async def test_agent_score_tracking_and_feedback() -> None:
    registry = UniversalAgentRegistry()
    agent_id = "agency-senior-developer"

    agent = await registry.get_agent(agent_id)
    if not agent:
        agent = (await registry.list_all_agents())[0]
        agent_id = agent.id

    initial_tasks = agent.score.tasks_completed

    await registry.record_task_outcome(
        agent_id=agent_id,
        success=True,
        confidence=0.95,
        cost=1.5,
        rating=5.0,
    )

    assert agent.score.tasks_completed == initial_tasks + 1
    assert agent.score.success_rate >= 0.90


# ── 5. Router Primitive Tools ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_router_primitive_tools_execution() -> None:
    registry = get_global_agent_registry()

    # 1. agent.search
    search_tool = AgentSearchTool(registry)
    s_res = await search_tool.execute({"query": "Frontend responsive design in React", "limit": 3})
    assert s_res.output["count"] >= 1
    assert len(s_res.evidence) >= 1

    # 2. agent.inspect
    top_agent_id = s_res.output["candidates"][0]["agent_id"]
    inspect_tool = AgentInspectTool(registry)
    i_res = await inspect_tool.execute({"agent_id": top_agent_id})
    assert i_res.output["id"] == top_agent_id
    assert "role" in i_res.output

    # 3. agent.spawn
    spawn_tool = AgentSpawnTool(registry)
    sp_res = await spawn_tool.execute({"agent_id": top_agent_id})
    assert sp_res.output["status"] == "active"
    assert "instance_id" in sp_res.output

    # 4. agent.delegate
    del_tool = AgentDelegateTool(registry)
    d_res = await del_tool.execute(
        {"agent_id": top_agent_id, "task": "Evaluate UI accessibility and layout responsiveness"}
    )
    assert d_res.output["status"] == "success"
    assert len(d_res.output["findings"]) >= 1

    # 5. agent.spawn_team
    team_tool = AgentSpawnTeamTool(registry)
    t_res = await team_tool.execute(
        {
            "objective": "Perform complete AppSec threat model and penetration test plan",
            "max_specialists": 3,
        }
    )
    assert t_res.output["status"] == "SUCCESS"

    # 6. agent.create
    create_tool = AgentCreateTool(registry)
    c_res = await create_tool.execute(
        {
            "name": "Custom BioInformatics Analyst",
            "role": "BioInformatics Scientist",
            "division": "research",
            "mission": "Analyze genomic sequence datasets.",
        }
    )
    assert c_res.output["status"] == "CREATED"


# ── 6. REST API Endpoints ──────────────────────────────────────────────────────


def test_router_api_endpoints() -> None:
    with TestClient(app) as client:
        # POST /api/v1/router/search
        resp_s = client.post(
            "/api/v1/router/search", json={"query": "Perform cloud finops audit", "limit": 3}
        )
        assert resp_s.status_code == 200
        s_data = resp_s.json()
        assert s_data["count"] >= 1

        # GET /api/v1/router/agents/{agent_id}
        top_id = s_data["candidates"][0]["agent_id"]
        resp_i = client.get(f"/api/v1/router/agents/{top_id}")
        assert resp_i.status_code == 200
        assert resp_i.json()["id"] == top_id

        # POST /api/v1/router/delegate
        resp_d = client.post(
            "/api/v1/router/delegate",
            json={"agent_id": top_id, "task": "Audit cloud infrastructure cost efficiency"},
        )
        assert resp_d.status_code == 200
        assert resp_d.json()["status"] == "success"

        # POST /api/v1/router/team
        resp_t = client.post(
            "/api/v1/router/team",
            json={
                "objective": "Launch new product landing page and analytics tracking",
                "max_specialists": 3,
            },
        )
        assert resp_t.status_code == 200
        assert resp_t.json()["status"] == "SUCCESS"

        # POST /api/v1/router/create
        resp_c = client.post(
            "/api/v1/router/create",
            json={
                "name": "Custom Logistics Optimizer",
                "role": "Supply Chain Strategist",
                "division": "operations",
                "mission": "Optimize warehouse inventory routing.",
            },
        )
        assert resp_c.status_code == 200
        assert resp_c.json()["status"] == "CREATED"

        # POST /api/v1/router/feedback
        resp_f = client.post(
            "/api/v1/router/feedback",
            json={
                "agent_id": top_id,
                "success": True,
                "confidence": 0.95,
                "cost": 1.0,
                "rating": 5.0,
            },
        )
        assert resp_f.status_code == 200
        assert resp_f.json()["status"] == "SUCCESS"


# ── 7. Jarvis Voice Chat Directive API ─────────────────────────────────────────


def test_jarvis_voice_chat_api() -> None:
    with TestClient(app) as client:
        resp = client.post("/api/jarvis/chat", json={"message": "Jarvis, open YouTube"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert "YouTube" in data["response"]
        assert len(data["tool_calls"]) >= 1
        assert data["tool_calls"][0]["name"] == "open_youtube"
