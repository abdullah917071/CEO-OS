"""Tests for CEO OS Executive Agent & ReAct Reasoning Engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.ceo_os_api.config import Settings
from apps.api.src.ceo_os_api.main import app
from ceo_agent.agent import CeoAIAgent
from ceo_agent.contracts import (
    CeoSubagentSpec,
)
from ceo_agent.llm import DeterministicCeoEngine
from ceo_agent.parser import CeoToolParser
from ceo_agent.prompting import CeoPromptFormatter
from ceo_agent.provider import CeoModelProvider
from ceo_agent.reflection import CeoReflectiveEngine
from ceo_agent.swarm import CeoSubagentSwarm
from ceo_agent.trajectory import CeoTrajectoryStore
from core.capabilities import CapabilityRegistry
from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from hermes import (
    HermesModelProvider,
)


class MockTimeTool(Tool):
    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="time.now",
            description="Get current ISO time",
            risk=RiskLevel.READ,
            input_schema={"type": "object", "properties": {}},
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        return ToolResult(
            output={"iso": "2026-08-16T12:00:00Z"},
            evidence=["Clock tick retrieved"],
        )


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        workspace_root=tmp_path / "workspace",
        openrouter_api_key="mock_key",
    )


@pytest.mark.asyncio
async def test_ceo_agent_parser_and_prompting() -> None:
    formatter = CeoPromptFormatter()
    prompt = formatter.format_system_prompt()
    assert "CEO OS Autonomous Executive AI Agent" in prompt

    raw_output = """<thought>
I need to query system time.
</thought>
<tool_call>
{"name": "time.now", "arguments": {}}
</tool_call>
"""
    thought = CeoToolParser.extract_thought(raw_output)
    assert thought == "I need to query system time."

    tool_calls = CeoToolParser.extract_tool_calls(raw_output)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "time.now"

    clean_ans = CeoToolParser.clean_final_answer(raw_output)
    assert clean_ans == ""


@pytest.mark.asyncio
async def test_ceo_agent_react_reasoning_loop() -> None:
    registry = CapabilityRegistry()
    registry.register(MockTimeTool())

    engine = DeterministicCeoEngine()
    agent = CeoAIAgent(capabilities=registry, llm=engine)

    result = await agent.run(task_id="test_task_1", objective="What is the current time?")
    assert result.status == "SUCCESS"
    assert len(result.trajectory.steps) >= 1
    assert any(s.tool_call and s.tool_call.name == "time.now" for s in result.trajectory.steps)
    assert result.reflection is not None


@pytest.mark.asyncio
async def test_ceo_agent_reflection_and_skill_synthesis() -> None:
    registry = CapabilityRegistry()
    registry.register(MockTimeTool())
    agent = CeoAIAgent(capabilities=registry)

    run_res = await agent.run(task_id="test_reflect_task", objective="Check clock")
    reflective_engine = CeoReflectiveEngine()

    reflection = await reflective_engine.reflect(run_res.trajectory, synthesize_skill=True)
    assert len(reflection.insights) >= 2
    skill_name = reflection.synthesized_skill.name
    assert "Check Clock" in skill_name or "test_reflect_task" in skill_name


@pytest.mark.asyncio
async def test_ceo_agent_trajectory_store_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CeoTrajectoryStore(storage_dir=Path(tmpdir))
        registry = CapabilityRegistry()
        agent = CeoAIAgent(capabilities=registry, trajectory_store=store)

        run_res = await agent.run(task_id="traj_task_1", objective="Perform action")
        assert store.get(run_res.trajectory.trajectory_id) is not None

        export_path = Path(tmpdir) / "export.jsonl"
        count = store.export_jsonl(export_path)
        assert count >= 1
        assert export_path.exists()
        assert "messages" in export_path.read_text()


@pytest.mark.asyncio
async def test_ceo_agent_subagent_swarm() -> None:
    agent = CeoAIAgent()
    swarm = CeoSubagentSwarm(agent)

    spec = CeoSubagentSpec(
        subagent_id="sub_worker_1",
        role="FinOps Analyst",
        objective="Inspect cloud cost metrics",
    )
    result = await swarm.spawn(spec)
    assert result.subagent_id == "sub_worker_1"
    assert result.status == "SUCCESS"


@pytest.mark.asyncio
async def test_ceo_model_provider_plan() -> None:
    provider = CeoModelProvider()
    caps = [MockTimeTool().spec]
    plan = await provider.plan("Get the time", caps)

    assert plan.objective == "Get the time"
    assert len(plan.steps) >= 1
    assert plan.steps[0].capability == "time.now"

    # Verify Hermes alias
    hermes_provider = HermesModelProvider()
    hermes_plan = await hermes_provider.plan("Get the time", caps)
    assert len(hermes_plan.steps) >= 1


@pytest.mark.asyncio
async def test_ceo_agent_fastapi_endpoints() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Run CeoAgent endpoint
        resp = await client.post(
            "/api/v1/ceo-agent/run",
            json={"task_id": "api_task_1", "objective": "What is the time?", "max_turns": 4},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert "run_id" in data

        # 2. Backwards compatibility Hermes endpoint
        h_resp = await client.post(
            "/api/v1/hermes/run",
            json={"task_id": "h_task_1", "objective": "What is the time?", "max_turns": 4},
        )
        assert h_resp.status_code == 200

        # 3. Status endpoints
        st_resp = await client.get("/api/v1/ceo-agent/status")
        assert st_resp.status_code == 200
        assert "CEO OS Executive ReAct Reasoning Engine" in st_resp.json()["engine"]

        # 4. Trajectories list
        tr_resp = await client.get("/api/v1/ceo-agent/trajectories")
        assert tr_resp.status_code == 200
        assert tr_resp.json()["count"] >= 1

        # 5. Subagent spawn
        sub_resp = await client.post(
            "/api/v1/ceo-agent/subagents/spawn",
            json={
                "role": "Security Auditor",
                "objective": "Review network policy",
                "allowed_capabilities": ["time.now"],
            },
        )
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "SUCCESS"
