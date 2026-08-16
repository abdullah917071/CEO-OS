from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from agents.contracts import WorkerAssignment, WorkerResult
from agents.repository import AgentRepository
from agents.runtime import AgentPolicyError, AgentRuntime
from agents.templates import AgentTemplateRegistry
from apps.api.src.ceo_os_api.database import create_database, initialize_schema
from core.contracts import RuntimeEvent


class RecordingEvents:
    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []

    async def publish(self, event: RuntimeEvent) -> None:
        self.events.append(event)


class ConcurrentExecutor:
    def __init__(self, *, cost_per_item: int = 1, delay: float = 0.03) -> None:
        self.active = 0
        self.max_active = 0
        self.cost_per_item = cost_per_item
        self.delay = delay

    async def execute(self, assignment: WorkerAssignment) -> WorkerResult:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(self.delay)
            return WorkerResult(
                output={
                    "comparisons": [
                        {"competitor": item, "pricing": "fixture"} for item in assignment.items
                    ]
                },
                evidence=[f"checked {item}" for item in assignment.items],
                confidence=0.8,
                uncertainty=["fixture data"],
                cost_units=len(assignment.items) * self.cost_per_item,
            )
        finally:
            self.active -= 1


async def build_runtime(path: Path, executor: Any) -> tuple[AgentRuntime, AgentRepository, Any]:
    engine, sessions = create_database(f"sqlite+aiosqlite:///{path}")
    await initialize_schema(engine)
    repository = AgentRepository(sessions)
    events = RecordingEvents()
    runtime = AgentRuntime(repository, AgentTemplateRegistry(), executor, events)
    await runtime.initialize()
    return runtime, repository, engine


@pytest.mark.asyncio
async def test_parallel_delegation_is_persistent_bounded_and_synthesized(tmp_path: Path) -> None:
    executor = ConcurrentExecutor()
    runtime, repository, engine = await build_runtime(tmp_path / "agents.db", executor)
    items = [f"Competitor {index}" for index in range(1, 11)]

    result = await runtime.delegate("Compare competitors", items, worker_count=4)

    assert result["status"] == "success"
    assert [item["competitor"] for item in result["comparisons"]] == items
    assert result["cost_units"] == 10
    assert executor.max_active >= 2
    assert len(result["workers"]) == 4
    agents = await repository.list_agents()
    assert len([agent for agent in agents if agent.kind == "temporary"]) == 4
    assert all(agent.status == "terminated" for agent in agents if agent.kind == "temporary")
    assignments = await repository.list_assignments()
    assert len(assignments) == 4
    assert all(assignment.status == "success" for assignment in assignments)
    director = next(agent for agent in agents if agent.name == "Research Director")
    assert len(await repository.inbox(director.id)) == 4

    restarted = AgentRepository(repository.sessions)
    assert len(await restarted.list_assignments()) == 4
    await runtime.shutdown()
    await engine.dispose()


@pytest.mark.asyncio
async def test_template_bounds_and_permanent_lifecycle_are_enforced(tmp_path: Path) -> None:
    runtime, repository, engine = await build_runtime(tmp_path / "policy.db", ConcurrentExecutor())
    ceo = next(agent for agent in await repository.list_agents() if agent.name == "CEO")
    with pytest.raises(AgentPolicyError, match="cannot exceed"):
        await runtime.create_agent(
            name="Overprivileged",
            template_name="researcher",
            parent_id=ceo.id,
            allowed_capabilities=["shell.execute"],
        )
    with pytest.raises(AgentPolicyError, match="Runtime budget"):
        await runtime.create_agent(
            name="Unbounded",
            template_name="researcher",
            parent_id=ceo.id,
            max_runtime_seconds=9_999,
        )
    with pytest.raises(AgentPolicyError, match="Permanent agents"):
        await runtime.pause_agent(ceo.id)

    worker = await runtime.create_agent(
        name="Lifecycle Worker", template_name="researcher", parent_id=ceo.id
    )
    with pytest.raises(AgentPolicyError, match="spawn authority"):
        await runtime.create_agent(
            name="Unauthorized Child", template_name="researcher", parent_id=worker.id
        )
    assert (await runtime.pause_agent(worker.id)).status == "paused"
    assert (await runtime.resume_agent(worker.id)).status == "active"
    clone = await runtime.clone_agent(worker.id, "Lifecycle Clone")
    assert clone.allowed_capabilities == worker.allowed_capabilities
    assert (await runtime.terminate_agent(worker.id)).status == "terminated"
    with pytest.raises(AgentPolicyError, match="terminated"):
        await runtime.resume_agent(worker.id)
    await runtime.shutdown()
    await engine.dispose()


@pytest.mark.asyncio
async def test_cost_overrun_fails_assignment_and_delegation(tmp_path: Path) -> None:
    runtime, repository, engine = await build_runtime(
        tmp_path / "cost.db", ConcurrentExecutor(cost_per_item=101)
    )
    result = await runtime.delegate("Cost bound", ["A"], worker_count=1)
    assert result["status"] == "failed"
    assignment = (await repository.list_assignments())[0]
    assert assignment.status == "failed"
    assert "cost budget" in (assignment.error or "")
    await runtime.shutdown()
    await engine.dispose()


@pytest.mark.asyncio
async def test_timeout_and_termination_cancel_active_assignments(tmp_path: Path) -> None:
    runtime, repository, engine = await build_runtime(
        tmp_path / "cancellation.db", ConcurrentExecutor(delay=2.0)
    )
    director = next(
        agent for agent in await repository.list_agents() if agent.name == "Research Director"
    )
    timed = await runtime.create_agent(
        name="Timed Worker",
        template_name="researcher",
        parent_id=director.id,
        max_runtime_seconds=1,
    )
    with pytest.raises(TimeoutError):
        await runtime.assign(timed.id, "Must time out", ["A"])
    assert (await repository.list_assignments())[0].status == "failed"

    cancellable = await runtime.create_agent(
        name="Cancellable Worker", template_name="researcher", parent_id=director.id
    )
    work = asyncio.create_task(runtime.assign(cancellable.id, "Cancel me", ["B"]))
    await asyncio.sleep(0.05)
    await runtime.terminate_agent(cancellable.id)
    with pytest.raises(asyncio.CancelledError):
        await work
    assignments = await repository.list_assignments()
    assert next(row for row in assignments if row.agent_id == cancellable.id).status == "cancelled"
    await runtime.shutdown()
    await engine.dispose()
