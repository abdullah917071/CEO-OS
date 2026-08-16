from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict
from typing import Any, TypedDict
from uuid import UUID, uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, interrupt

from apps.api.src.ceo_os_api.database import TaskRecord, TaskRepository
from core.capabilities import CapabilityRegistry
from core.contracts import (
    EpisodeRecorder,
    EventPublisher,
    RuntimeEvent,
    StepStatus,
    TaskControl,
    TaskStatus,
    ToolResult,
)
from core.model_router import ModelRouter


class TransientExecutionError(Exception):
    """A tool failure that is safe for the graph retry policy to retry."""


class ExecutionState(TypedDict, total=False):
    task_id: str
    message: str
    objective: str
    plan: dict[str, Any]
    step_index: int
    outputs: list[dict[str, Any]]
    evidence: list[str]
    cancelled: bool


class CeoRuntime:
    def __init__(
        self,
        tasks: TaskRepository,
        capabilities: CapabilityRegistry,
        models: ModelRouter,
        events: EventPublisher,
        checkpointer: BaseCheckpointSaver[Any],
        memory: EpisodeRecorder | None = None,
    ) -> None:
        self.tasks, self.capabilities, self.models = tasks, capabilities, models
        self.events = events
        self.memory = memory
        self.graph = self._build_graph(checkpointer)

    def _build_graph(self, checkpointer: BaseCheckpointSaver[Any]) -> Any:
        builder = StateGraph(ExecutionState)
        builder.add_node("plan", self._plan)
        builder.add_node("control", self._control)
        builder.add_node(
            "execute",
            self._execute,
            retry_policy=RetryPolicy(
                max_attempts=3,
                initial_interval=0.1,
                backoff_factor=2.0,
                max_interval=1.0,
                jitter=False,
                retry_on=TransientExecutionError,
            ),
        )
        builder.add_node("success", self._success)
        builder.add_node("cancelled", self._cancelled)
        builder.add_edge(START, "plan")
        builder.add_edge("plan", "control")
        builder.add_conditional_edges(
            "control",
            self._route,
            {"execute": "execute", "success": "success", "cancelled": "cancelled"},
        )
        builder.add_edge("execute", "control")
        builder.add_edge("success", END)
        builder.add_edge("cancelled", END)
        return builder.compile(checkpointer=checkpointer)

    async def create(
        self, message: str, idempotency_key: str | None = None
    ) -> tuple[TaskRecord, bool]:
        task, created = await self.tasks.create(message, idempotency_key)
        if created:
            await self.events.publish(
                RuntimeEvent("task.created", UUID(task.id), {"message": message})
            )
        return task, created

    async def execute(self, task_id: UUID, *, resume: bool = False) -> TaskRecord:
        task = await self.tasks.get(task_id)
        if task is None:
            raise KeyError(str(task_id))
        config = {"configurable": {"thread_id": str(task_id)}}
        try:
            snapshot = await self.graph.aget_state(config)
            if resume and snapshot.values:
                graph_input: Any = Command(resume=True)
            elif snapshot.values:
                graph_input = None
            else:
                graph_input = {
                    "task_id": task.id,
                    "message": task.message,
                    "step_index": 0,
                    "outputs": [],
                    "evidence": [],
                    "cancelled": False,
                }
            await self.graph.ainvoke(graph_input, config=config)
        except Exception as exc:
            await self.tasks.update(task_id, status=TaskStatus.FAILED, error=str(exc))
            await self.events.publish(RuntimeEvent("task.failed", task_id, {"error": str(exc)}))
        result = await self.tasks.get(task_id)
        if result is None:
            raise KeyError(str(task_id))
        return result

    async def _plan(self, state: ExecutionState) -> ExecutionState:
        task_id = UUID(state["task_id"])
        if state.get("plan"):
            return {}
        await self.tasks.update(task_id, status=TaskStatus.PLANNING)
        provider = self.models.for_role("ceo_planner")
        plan = await provider.plan(state["message"], self.capabilities.list())
        plan_data = asdict(plan)
        await self.tasks.update(
            task_id, objective=plan.objective, status=TaskStatus.RUNNING, plan=plan_data
        )
        await self.events.publish(RuntimeEvent("task.running", task_id, {"plan": plan_data}))
        return {"objective": plan.objective, "plan": plan_data}

    async def _control(self, state: ExecutionState) -> ExecutionState:
        task_id = UUID(state["task_id"])
        task = await self.tasks.get(task_id)
        if task is None:
            raise KeyError(str(task_id))
        if task.control == TaskControl.CANCEL:
            return {"cancelled": True}
        if task.control == TaskControl.PAUSE:
            await self.tasks.update(task_id, status=TaskStatus.WAITING)
            await self.events.publish(RuntimeEvent("task.paused", task_id, {}))
            interrupt({"reason": "paused", "task_id": str(task_id)})
        await self.tasks.update(task_id, status=TaskStatus.RUNNING)
        return {}

    def _route(self, state: ExecutionState) -> str:
        if state.get("cancelled"):
            return "cancelled"
        steps = state.get("plan", {}).get("steps", [])
        return "execute" if state.get("step_index", 0) < len(steps) else "success"

    async def _execute(self, state: ExecutionState) -> ExecutionState:
        task_id, index = UUID(state["task_id"]), state.get("step_index", 0)
        step = state["plan"]["steps"][index]
        canonical = json.dumps(step["arguments"], sort_keys=True, separators=(",", ":"))
        key = hashlib.sha256(
            f"{task_id}:{index}:{step['capability']}:{canonical}".encode()
        ).hexdigest()
        existing = await self.tasks.get_step(task_id, index)
        if existing is not None and existing.status == StepStatus.SUCCESS:
            result = ToolResult(existing.output or {}, existing.evidence)
        else:
            record = await self.tasks.begin_step(
                task_id, index, step["capability"], step["arguments"], key
            )
            await self.events.publish(
                RuntimeEvent(
                    "task.step.started", task_id, {"index": index, "capability": step["capability"]}
                )
            )
            try:
                result = await self.capabilities.execute(
                    step["capability"], step["arguments"], idempotency_key=key
                )
            except (ConnectionError, TimeoutError) as exc:
                await self.tasks.fail_step(record.id, str(exc))
                raise TransientExecutionError(str(exc)) from exc
            except Exception as exc:
                await self.tasks.fail_step(record.id, str(exc))
                raise
            await self.tasks.complete_step(record.id, result)
            await self.events.publish(
                RuntimeEvent(
                    "task.step.completed", task_id, {"index": index, "evidence": result.evidence}
                )
            )
        return {
            "step_index": index + 1,
            "outputs": [
                *state.get("outputs", []),
                {"capability": step["capability"], "output": result.output},
            ],
            "evidence": [*state.get("evidence", []), *result.evidence],
        }

    async def _success(self, state: ExecutionState) -> ExecutionState:
        task_id = UUID(state["task_id"])
        outputs = state.get("outputs", [])
        message = (
            "Completed."
            if state.get("plan", {}).get("steps")
            else ("Acknowledged; no supported action was required.")
        )
        if outputs and outputs[-1]["capability"] == "memory.remember":
            message = "Stored in permanent memory."
        elif outputs and outputs[-1]["capability"] == "memory.search":
            memories = outputs[-1]["output"].get("memories", [])
            message = (
                "I remember: " + " | ".join(item["content"] for item in memories)
                if memories
                else "I could not find a relevant active memory."
            )
        result = {
            "message": message,
            "outputs": outputs,
            "evidence": state.get("evidence", []),
            "model_provider": self.models.for_role("ceo_planner").name,
        }
        if self.memory is not None:
            await self.memory.record_task_episode(task_id, state["objective"], result)
        await self.tasks.update(task_id, status=TaskStatus.SUCCESS, result=result, error=None)
        await self.events.publish(RuntimeEvent("task.completed", task_id, result))
        return {}

    async def _cancelled(self, state: ExecutionState) -> ExecutionState:
        task_id = UUID(state["task_id"])
        await self.tasks.update(task_id, status=TaskStatus.CANCELLED)
        await self.events.publish(RuntimeEvent("task.cancelled", task_id, {}))
        return {}


class TaskRunner:
    def __init__(self, runtime: CeoRuntime, lease_seconds: int = 30) -> None:
        self.runtime, self.lease_seconds, self.owner = runtime, lease_seconds, str(uuid4())
        self._running: dict[UUID, asyncio.Task[None]] = {}

    def start(self, task_id: UUID, *, resume: bool = False) -> None:
        active = self._running.get(task_id)
        if active is not None and not active.done():
            if resume:
                self._running[task_id] = asyncio.create_task(
                    self._run_after(active, task_id, resume=True)
                )
            return
        self._running[task_id] = asyncio.create_task(self._run(task_id, resume))

    async def _run_after(
        self, previous: asyncio.Task[None], task_id: UUID, *, resume: bool
    ) -> None:
        await asyncio.gather(previous, return_exceptions=True)
        await self._run(task_id, resume)

    async def _run(self, task_id: UUID, resume: bool) -> None:
        if not await self.runtime.tasks.acquire_lease(task_id, self.owner, self.lease_seconds):
            return
        heartbeat = asyncio.create_task(self._heartbeat(task_id))
        try:
            await self.runtime.execute(task_id, resume=resume)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await self.runtime.tasks.release_lease(task_id, self.owner)

    async def _heartbeat(self, task_id: UUID) -> None:
        while True:
            await asyncio.sleep(self.lease_seconds / 3)
            if not await self.runtime.tasks.renew_lease(task_id, self.owner, self.lease_seconds):
                return

    async def recover(self) -> None:
        for task in await self.runtime.tasks.recoverable():
            if task.control != TaskControl.PAUSE:
                self.start(
                    UUID(task.id), resume=task.status in {TaskStatus.QUEUED, TaskStatus.WAITING}
                )

    async def shutdown(self) -> None:
        for task in self._running.values():
            task.cancel()
        await asyncio.gather(*self._running.values(), return_exceptions=True)
