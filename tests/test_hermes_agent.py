"""Unit and integration tests for Nous Research Hermes AI Agent integration in CEO OS."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.ceo_os_api.main import app
from core.capabilities import CapabilityRegistry
from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from hermes.agent import HermesAIAgent
from hermes.integration import HermesIntegration
from hermes.parser import HermesToolParser
from hermes.prompting import HermesPromptFormatter
from hermes.provider import HermesModelProvider
from hermes.swarm import HermesSubagentSwarm
from hermes.tools import (
    HermesAgentRunTool,
    HermesReflectSynthesizeTool,
    HermesSubagentSpawnTool,
    HermesTrajectoryExportTool,
)
from hermes.trajectory import HermesTrajectoryStore
from integrations.router import CapabilityRouter


class MockEchoTool(Tool):
    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="echo.test",
            description="Echoes the input parameter",
            input_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
            risk=RiskLevel.READ,
            source="internal",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        return ToolResult(
            output={"echoed": arguments.get("msg", "hello")},
            evidence=["Echo verified"],
        )


class MockCostTool(Tool):
    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="production.cost.overview",
            description="Retrieves current cloud spend",
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.READ,
            source="integration:production",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key, arguments
        return ToolResult(
            output={
                "current_mtd_spend": 3250.0,
                "monthly_budget": 10000.0,
                "waste_detected": 420.0,
            },
            evidence=["FinOps spend retrieved from AWS billing"],
        )


@pytest.mark.asyncio
async def test_hermes_prompt_formatter() -> None:
    caps = [MockEchoTool().spec, MockCostTool().spec]
    schema = HermesPromptFormatter.format_tool_schema(caps)
    assert "echo.test" in schema
    assert "production.cost.overview" in schema

    prompt = HermesPromptFormatter.build_system_prompt(
        caps,
        memory_context=["Budget threshold is $10k/month"],
        rules=["Never make destructive cloud changes without approval"],
    )
    assert "Hermes 3" in prompt
    assert "<tools>" in prompt
    assert "Long-Term Memory Context" in prompt
    assert "Budget threshold is $10k/month" in prompt
    assert "Never make destructive cloud changes" in prompt


@pytest.mark.asyncio
async def test_hermes_tool_parser() -> None:
    sample_text = """
<thought>
I need to inspect the FinOps cloud spend first before taking action.
</thought>
<tool_call>
{"name": "production.cost.overview", "arguments": {}}
</tool_call>
"""
    thought = HermesToolParser.extract_thought(sample_text)
    assert "inspect the FinOps cloud spend" in thought

    calls = HermesToolParser.extract_tool_calls(sample_text)
    assert len(calls) == 1
    assert calls[0].name == "production.cost.overview"
    assert calls[0].arguments == {}

    cleaned = HermesToolParser.strip_tool_tags(sample_text)
    assert "<thought>" not in cleaned
    assert "<tool_call>" not in cleaned


@pytest.mark.asyncio
async def test_hermes_react_execution_loop(tmp_path: Path) -> None:
    registry = CapabilityRegistry([MockEchoTool(), MockCostTool()])
    store = HermesTrajectoryStore(storage_dir=tmp_path / "trajectories")
    agent = HermesAIAgent(capabilities=registry, trajectory_store=store)

    result = await agent.run(
        task_id="task_test_001",
        objective="Audit AWS FinOps cloud spend and report anomalies",
        max_turns=4,
    )

    assert result.status == "SUCCESS"
    assert len(result.trajectory.steps) >= 1
    tool_names = [s.tool_call.name for s in result.trajectory.steps if s.tool_call]
    assert "production.cost.overview" in tool_names
    assert any("FinOps spend" in ev for ev in result.evidence)
    assert result.reflection is not None
    assert len(result.reflection.insights) > 0

    saved_traj = store.get(result.trajectory.trajectory_id)
    assert saved_traj is not None
    assert saved_traj.task_id == "task_test_001"


@pytest.mark.asyncio
async def test_hermes_reflection_and_skill_synthesis(tmp_path: Path) -> None:
    registry = CapabilityRegistry([MockCostTool()])
    store = HermesTrajectoryStore(storage_dir=tmp_path / "trajectories")
    agent = HermesAIAgent(capabilities=registry, trajectory_store=store)

    result = await agent.run(
        task_id="task_test_002",
        objective="Inspect monthly AWS cloud costs",
        max_turns=3,
    )

    assert result.reflection is not None
    skill = result.reflection.synthesized_skill
    assert skill is not None
    assert "hermes-auto-" in skill.name
    assert "SKILL.md" or "Core Mission" in skill.content_markdown
    assert "production.cost.overview" in skill.content_markdown


@pytest.mark.asyncio
async def test_hermes_trajectory_export(tmp_path: Path) -> None:
    registry = CapabilityRegistry([MockCostTool()])
    store = HermesTrajectoryStore(storage_dir=tmp_path / "trajectories")
    agent = HermesAIAgent(capabilities=registry, trajectory_store=store)

    await agent.run(
        task_id="task_export_001",
        objective="Audit AWS cloud costs",
    )

    export_path = tmp_path / "dataset.jsonl"
    jsonl_str = store.export_jsonl(export_path)
    assert export_path.exists()
    assert "conversations" in jsonl_str
    assert "production.cost.overview" in jsonl_str


@pytest.mark.asyncio
async def test_hermes_subagent_swarm() -> None:
    registry = CapabilityRegistry([MockEchoTool(), MockCostTool()])
    swarm = HermesSubagentSwarm(registry)

    spec = swarm.create_spec(
        role="CloudFinopsSpecialist",
        objective="Analyze cloud spend spikes",
        allowed_capabilities=["production.cost.overview"],
    )

    result = await swarm.spawn_and_execute(spec)
    assert result.status == "SUCCESS"
    assert "CloudFinopsSpecialist" in result.output
    assert len(result.evidence) >= 2


@pytest.mark.asyncio
async def test_hermes_model_provider() -> None:
    provider = HermesModelProvider()
    assert provider.name == "hermes"

    plan = await provider.plan(
        "Audit cloud costs and FinOps spend",
        [MockCostTool().spec],
    )
    assert plan.objective == "Audit cloud costs and FinOps spend"
    assert len(plan.steps) >= 1
    assert plan.steps[0].capability == "production.cost.overview"


@pytest.mark.asyncio
async def test_hermes_capability_tools_and_router() -> None:
    agent = HermesAIAgent()
    run_tool = HermesAgentRunTool(agent)
    reflect_tool = HermesReflectSynthesizeTool(agent)
    export_tool = HermesTrajectoryExportTool(agent)
    subagent_tool = HermesSubagentSpawnTool(agent)

    integration = HermesIntegration(agent=agent)
    manifest = integration.manifest()
    assert manifest.name == "hermes_agent"
    assert len(integration.build_tools()) == 4

    router = CapabilityRouter()
    domains = router.classify_domains("Execute autonomous hermes react loop trajectory")
    assert "integrations" in domains

    run_res = await run_tool.execute({"task_id": "t1", "objective": "Check cloud spend"})
    assert run_res.output["status"] == "SUCCESS"
    traj_id = run_res.output["trajectory"]["trajectory_id"]

    reflect_res = await reflect_tool.execute({"trajectory_id": traj_id})
    assert len(reflect_res.output["insights"]) > 0

    export_res = await export_tool.execute({})
    assert export_res.output["count"] >= 1

    sub_res = await subagent_tool.execute({"role": "Researcher", "objective": "Research topic"})
    assert sub_res.output["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_hermes_fastapi_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/hermes/status")
        assert res.status_code == 200
        data = res.json()
        assert "CEO OS" in data["engine"] or "Hermes" in data["engine"]

        res = await client.post(
            "/api/v1/hermes/run",
            json={
                "task_id": "api_task_01",
                "objective": "Audit AWS FinOps costs",
                "max_turns": 4,
            },
        )
        assert res.status_code == 200
        run_data = res.json()
        assert run_data["status"] == "SUCCESS"
        assert run_data["task_id"] == "api_task_01"

        res = await client.get("/api/v1/hermes/trajectories")
        assert res.status_code == 200
        traj_data = res.json()
        assert traj_data["count"] >= 1
        traj_id = traj_data["trajectories"][0]["trajectory_id"]

        res = await client.post(
            "/api/v1/hermes/reflect",
            json={"trajectory_id": traj_id},
        )
        assert res.status_code == 200
        ref_data = res.json()
        assert len(ref_data["insights"]) >= 1

        res = await client.post(
            "/api/v1/hermes/subagents/spawn",
            json={"role": "FinOpsWorker", "objective": "Analyze EC2 instances"},
        )
        assert res.status_code == 200
        sub_data = res.json()
        assert sub_data["status"] == "SUCCESS"
        assert sub_data["objective"] == "Analyze EC2 instances"
        assert sub_data["output"]
