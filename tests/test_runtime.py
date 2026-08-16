from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.src.ceo_os_api.checkpoints import open_checkpointer
from apps.api.src.ceo_os_api.database import Base, TaskRepository
from apps.api.src.ceo_os_api.events import EventHub
from apps.api.src.ceo_os_api.planner import DeterministicProvider
from apps.api.src.ceo_os_api.runtime import CeoRuntime
from core.capabilities import CapabilityRegistry
from core.contracts import (
    CapabilitySpec,
    ExecutionPlan,
    PlanStep,
    RiskLevel,
    TaskControl,
    TaskStatus,
    ToolResult,
)
from core.model_router import ModelRouter
from tools.builtin import built_in_tools


async def make_runtime(
    tmp_path: Path, tools: list[Any] | None = None, provider: Any = None
) -> CeoRuntime:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tasks.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    selected_provider = provider or DeterministicProvider()
    runtime = CeoRuntime(
        TaskRepository(sessions),
        CapabilityRegistry(tools or built_in_tools(tmp_path / "workspace")),
        ModelRouter({selected_provider.name: selected_provider}, selected_provider.name),
        EventHub(),
        InMemorySaver(),
    )
    runtime._test_engine = engine  # type: ignore[attr-defined]
    return runtime


@pytest.mark.asyncio
async def test_phase_one_filesystem_acceptance_scenario(tmp_path: Path) -> None:
    runtime = await make_runtime(tmp_path)
    task, created = await runtime.create(
        "Create a folder called project-x, write a README describing the project, "
        "and tell me where you put it."
    )
    assert created
    task = await runtime.execute(UUID(task.id))

    assert task.status == TaskStatus.SUCCESS
    assert (tmp_path / "workspace/project-x/README.md").is_file()
    assert task.result is not None
    assert any("README.md" in item for item in task.result["evidence"])


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_original_task(tmp_path: Path) -> None:
    runtime = await make_runtime(tmp_path)
    first, first_created = await runtime.create("What time is it?", "request-123")
    second, second_created = await runtime.create("Different request", "request-123")
    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert len(await runtime.tasks.list()) == 1


class StaticProvider:
    name = "static"

    async def plan(self, message: str, capabilities: list[CapabilitySpec]) -> ExecutionPlan:
        del message, capabilities
        return ExecutionPlan(
            "Retry a transient operation",
            ["Tool succeeds"],
            [PlanStep("test.flaky", {}, "Tool succeeds")],
        )


class FlakyTool:
    def __init__(self) -> None:
        self.attempts = 0

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec("test.flaky", "Transient test tool", {}, RiskLevel.READ)

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments
        del idempotency_key
        self.attempts += 1
        if self.attempts < 3:
            raise ConnectionError("temporary")
        return ToolResult({"ok": True}, ["Transient operation recovered"])


class PermanentTool:
    def __init__(self) -> None:
        self.attempts = 0

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec("test.flaky", "Permanent failure test tool", {}, RiskLevel.READ)

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        self.attempts += 1
        raise ValueError("invalid request")


class TwoStepProvider:
    name = "two-step"

    async def plan(self, message: str, capabilities: list[CapabilitySpec]) -> ExecutionPlan:
        del message, capabilities
        return ExecutionPlan(
            "Run two durable steps",
            ["First completes", "Second completes"],
            [
                PlanStep("test.first", {}, "First completes"),
                PlanStep("test.second", {}, "Second completes"),
            ],
        )


class CountingTool:
    def __init__(self, name: str, block: bool = False) -> None:
        self.name, self.block, self.calls = name, block, 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(self.name, "Count executions", {}, RiskLevel.READ)

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments
        del idempotency_key
        self.calls += 1
        self.started.set()
        if self.block:
            await self.release.wait()
        return ToolResult({"calls": self.calls}, [f"{self.name} completed"])


@pytest.mark.asyncio
async def test_transient_failure_retries_with_bounded_policy(tmp_path: Path) -> None:
    tool = FlakyTool()
    runtime = await make_runtime(tmp_path, [tool], StaticProvider())
    task, _ = await runtime.create("retry")
    task = await runtime.execute(UUID(task.id))
    step = await runtime.tasks.get_step(UUID(task.id), 0)
    assert task.status == TaskStatus.SUCCESS
    assert tool.attempts == 3
    assert step is not None and step.attempts == 3


@pytest.mark.asyncio
async def test_permanent_failure_is_not_retried(tmp_path: Path) -> None:
    tool = PermanentTool()
    runtime = await make_runtime(tmp_path, [tool], StaticProvider())
    task, _ = await runtime.create("fail")
    task = await runtime.execute(UUID(task.id))
    step = await runtime.tasks.get_step(UUID(task.id), 0)
    assert task.status == TaskStatus.FAILED
    assert tool.attempts == 1
    assert step is not None and step.attempts == 1


@pytest.mark.asyncio
async def test_pause_resume_and_cancel_are_checkpointed_controls(tmp_path: Path) -> None:
    runtime = await make_runtime(tmp_path)
    paused, _ = await runtime.create("What time is it?")
    paused_id = UUID(paused.id)
    await runtime.tasks.set_control(paused_id, TaskControl.PAUSE)
    paused = await runtime.execute(paused_id)
    assert paused.status == TaskStatus.WAITING

    await runtime.tasks.update(paused_id, control=TaskControl.RUN, status=TaskStatus.QUEUED)
    resumed = await runtime.execute(paused_id, resume=True)
    assert resumed.status == TaskStatus.SUCCESS

    cancelled, _ = await runtime.create("What time is it?")
    cancelled_id = UUID(cancelled.id)
    await runtime.tasks.set_control(cancelled_id, TaskControl.CANCEL)
    cancelled = await runtime.execute(cancelled_id)
    assert cancelled.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_task_lease_has_single_owner(tmp_path: Path) -> None:
    runtime = await make_runtime(tmp_path)
    task, _ = await runtime.create("What time is it?")
    task_id = UUID(task.id)
    assert await runtime.tasks.acquire_lease(task_id, "runner-a", 30)
    assert not await runtime.tasks.acquire_lease(task_id, "runner-b", 30)
    await runtime.tasks.release_lease(task_id, "runner-a")
    assert await runtime.tasks.acquire_lease(task_id, "runner-b", 30)

    await runtime.tasks.release_lease(task_id, "runner-b")
    assert await runtime.tasks.acquire_lease(task_id, "expired-runner", 0)
    assert await runtime.tasks.acquire_lease(task_id, "recovery-runner", 30)


@pytest.mark.asyncio
async def test_restart_resumes_from_last_checkpoint_without_repeating_completed_step(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'durable.db'}"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    repository = TaskRepository(async_sessionmaker(engine, expire_on_commit=False))
    first, second = CountingTool("test.first"), CountingTool("test.second", block=True)
    provider = TwoStepProvider()
    registry = CapabilityRegistry([first, second])
    router = ModelRouter({provider.name: provider}, provider.name)
    checkpoint_url = f"sqlite+aiosqlite:///{tmp_path / 'checkpoints.db'}"

    async with open_checkpointer(checkpoint_url) as saver:
        runtime = CeoRuntime(repository, registry, router, EventHub(), saver)
        task, _ = await runtime.create("durable")
        task_id = UUID(task.id)
        execution = asyncio.create_task(runtime.execute(task_id))
        await asyncio.wait_for(second.started.wait(), timeout=2)
        execution.cancel()
        with pytest.raises(asyncio.CancelledError):
            await execution

    second.block = False
    second.release.set()
    async with open_checkpointer(checkpoint_url) as saver:
        restarted = CeoRuntime(repository, registry, router, EventHub(), saver)
        result = await restarted.execute(task_id)

    assert result.status == TaskStatus.SUCCESS
    assert first.calls == 1
    assert second.calls == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_unsupported_request_is_acknowledged_without_fake_action() -> None:
    provider = DeterministicProvider()
    plan = await provider.plan("Launch a Meta campaign", [])
    assert plan.steps == []
    assert "unsupported action" in plan.success_conditions[0]
