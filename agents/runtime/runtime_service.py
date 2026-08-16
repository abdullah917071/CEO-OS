"""Agent Runtime service: orchestrates persistent agent entities, policy boundaries, and delegation."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from uuid import uuid4

from agents.contracts import (
    AgentKind,
    AgentStatus,
    AssignmentStatus,
    WorkerAssignment,
    WorkerExecutor,
    WorkerResult,
)
from agents.repository import AgentAssignmentRecord, AgentRecord, AgentRepository
from agents.templates import AgentTemplateRegistry
from core.contracts import EventPublisher, RuntimeEvent


class AgentPolicyError(ValueError):
    pass


class DeterministicResearchExecutor:
    """Offline orchestration fixture. Outputs are explicitly synthetic, not market facts."""

    async def execute(self, assignment: WorkerAssignment) -> WorkerResult:
        await asyncio.sleep(0.02)
        comparisons = [
            {
                "competitor": item,
                "pricing": "simulation: unknown",
                "features": ["simulation fixture"],
                "advertising": "simulation: not observed",
            }
            for item in assignment.items
        ]
        return WorkerResult(
            output={"comparisons": comparisons, "data_classification": "simulation"},
            evidence=[f"Simulation worker processed {item}" for item in assignment.items],
            confidence=1.0,
            uncertainty=["No live market sources were queried"],
            cost_units=len(assignment.items),
        )


class AgentRuntime:
    def __init__(
        self,
        repository: AgentRepository,
        templates: AgentTemplateRegistry,
        executor: WorkerExecutor,
        events: EventPublisher,
        *,
        global_max_concurrency: int = 10,
    ) -> None:
        if global_max_concurrency < 1:
            raise ValueError("global_max_concurrency must be positive")
        self.repository = repository
        self.templates = templates
        self.executor = executor
        self.events = events
        self._semaphore = asyncio.Semaphore(global_max_concurrency)
        self._running: dict[str, asyncio.Task[AgentAssignmentRecord]] = {}

    async def initialize(self) -> None:
        ceo = await self.repository.ensure_permanent("CEO", "Chief Executive")
        director = await self.repository.ensure_permanent("Research Director", "Research Director")
        if director.parent_id != ceo.id:
            await self.repository.update_agent(director.id, parent_id=ceo.id)

    async def create_agent(
        self,
        *,
        name: str,
        template_name: str,
        parent_id: str | None,
        allowed_capabilities: list[str] | None = None,
        data_scope: list[str] | None = None,
        max_runtime_seconds: int | None = None,
        max_cost_units: int | None = None,
        max_concurrency: int | None = None,
    ) -> AgentRecord:
        template = self.templates.get(template_name)
        requested_capabilities = set(allowed_capabilities or template.allowed_capabilities)
        requested_scope = set(data_scope or template.data_scope)
        if not requested_capabilities <= template.allowed_capabilities:
            raise AgentPolicyError("Agent capabilities cannot exceed its template")
        if not requested_scope <= template.data_scope:
            raise AgentPolicyError("Agent data scope cannot exceed its template")
        runtime = max_runtime_seconds or template.budget.max_runtime_seconds
        cost = max_cost_units or template.budget.max_cost_units
        concurrency = max_concurrency or template.budget.max_concurrency
        if not 1 <= runtime <= template.budget.max_runtime_seconds:
            raise AgentPolicyError("Runtime budget exceeds template")
        if not 1 <= cost <= template.budget.max_cost_units:
            raise AgentPolicyError("Cost budget exceeds template")
        if not 1 <= concurrency <= template.budget.max_concurrency:
            raise AgentPolicyError("Concurrency budget exceeds template")
        if parent_id:
            parent = await self.repository.get_agent(parent_id)
            if parent is None:
                raise AgentPolicyError("Parent agent does not exist")
            if parent.status != AgentStatus.ACTIVE or not parent.can_spawn_agents:
                raise AgentPolicyError("Parent agent has no active spawn authority")
        record = await self.repository.create_agent(
            name=name.strip(),
            role=template.role,
            kind=AgentKind.TEMPORARY,
            status=AgentStatus.ACTIVE,
            template_name=template.name,
            template_version=template.version,
            parent_id=parent_id,
            allowed_capabilities=sorted(requested_capabilities),
            data_scope=sorted(requested_scope),
            model_class=template.model_class,
            can_spawn_agents=template.can_spawn_agents,
            max_runtime_seconds=runtime,
            max_cost_units=cost,
            max_concurrency=concurrency,
            terminated_at=None,
        )
        await self.events.publish(
            RuntimeEvent(
                "agent.created",
                None,
                {"agent_id": record.id, "name": record.name, "template": template_name},
            )
        )
        return record

    async def clone_agent(self, agent_id: str, name: str) -> AgentRecord:
        source = await self._require_agent(agent_id)
        if source.kind != AgentKind.TEMPORARY:
            raise AgentPolicyError("Only temporary agents can be cloned")
        return await self.create_agent(
            name=name,
            template_name=source.template_name,
            parent_id=source.parent_id,
            allowed_capabilities=source.allowed_capabilities,
            data_scope=source.data_scope,
            max_runtime_seconds=source.max_runtime_seconds,
            max_cost_units=source.max_cost_units,
            max_concurrency=source.max_concurrency,
        )

    async def update_agent(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        max_runtime_seconds: int | None = None,
        max_cost_units: int | None = None,
    ) -> AgentRecord:
        agent = await self._require_mutable_agent(agent_id)
        template = self.templates.get(agent.template_name)
        changes: dict[str, Any] = {}
        if name is not None:
            changes["name"] = name.strip()
        if max_runtime_seconds is not None:
            if not 1 <= max_runtime_seconds <= template.budget.max_runtime_seconds:
                raise AgentPolicyError("Runtime budget exceeds template")
            changes["max_runtime_seconds"] = max_runtime_seconds
        if max_cost_units is not None:
            if not 1 <= max_cost_units <= template.budget.max_cost_units:
                raise AgentPolicyError("Cost budget exceeds template")
            changes["max_cost_units"] = max_cost_units
        return await self.repository.update_agent(agent_id, **changes)

    async def pause_agent(self, agent_id: str) -> AgentRecord:
        agent = await self._require_mutable_agent(agent_id)
        if agent.status != AgentStatus.ACTIVE:
            raise AgentPolicyError("Agent is not active")
        record = await self.repository.update_agent(agent_id, status=AgentStatus.PAUSED)
        await self.events.publish(RuntimeEvent("agent.paused", None, {"agent_id": agent_id}))
        return record

    async def resume_agent(self, agent_id: str) -> AgentRecord:
        agent = await self._require_mutable_agent(agent_id)
        if agent.status != AgentStatus.PAUSED:
            raise AgentPolicyError("Agent is not paused")
        record = await self.repository.update_agent(agent_id, status=AgentStatus.ACTIVE)
        await self.events.publish(RuntimeEvent("agent.resumed", None, {"agent_id": agent_id}))
        return record

    async def terminate_agent(self, agent_id: str) -> AgentRecord:
        await self._require_mutable_agent(agent_id)
        running = self._running.get(agent_id)
        if running and not running.done():
            running.cancel()
        record = await self.repository.update_agent(
            agent_id, status=AgentStatus.TERMINATED, terminated_at=datetime.now(UTC)
        )
        await self.events.publish(RuntimeEvent("agent.terminated", None, {"agent_id": agent_id}))
        return record

    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        payload: dict[str, Any],
        assignment_id: str | None = None,
    ) -> object:
        await self._require_agent(sender_id)
        await self._require_agent(recipient_id)
        record = await self.repository.create_message(
            sender_id, recipient_id, message_type, payload, assignment_id
        )
        await self.events.publish(
            RuntimeEvent(
                "agent.message.sent",
                None,
                {
                    "message_id": record.id,
                    "sender_id": sender_id,
                    "recipient_id": recipient_id,
                    "message_type": message_type,
                },
            )
        )
        return record

    async def assign(
        self,
        agent_id: str,
        objective: str,
        items: list[str],
        *,
        context: dict[str, Any] | None = None,
        delegation_id: str | None = None,
    ) -> AgentAssignmentRecord:
        agent = await self._require_agent(agent_id)
        if agent.status != AgentStatus.ACTIVE:
            raise AgentPolicyError("Agent is not active")
        if not objective.strip() or not 1 <= len(items) <= 100:
            raise AgentPolicyError("Assignment requires an objective and 1 to 100 items")
        record = await self.repository.create_assignment(
            delegation_id or str(uuid4()), agent.id, objective, items, context or {}
        )
        task = asyncio.create_task(self._execute_assignment(agent, record))
        self._running[agent.id] = task
        try:
            return await task
        finally:
            self._running.pop(agent.id, None)

    async def delegate(
        self,
        objective: str,
        items: list[str],
        *,
        worker_count: int = 4,
        template_name: str = "researcher",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not objective.strip():
            raise AgentPolicyError("Objective cannot be empty")
        if not 1 <= len(items) <= 100 or any(not item.strip() for item in items):
            raise AgentPolicyError("Delegation requires 1 to 100 items")
        if len(set(items)) != len(items):
            raise AgentPolicyError("Delegation items must be unique")
        if not 1 <= worker_count <= 10:
            raise AgentPolicyError("Worker count must be between 1 and 10")
        worker_count = min(worker_count, len(items))
        director = next(
            (
                agent
                for agent in await self.repository.list_agents()
                if agent.name == "Research Director" and agent.status == AgentStatus.ACTIVE
            ),
            None,
        )
        if director is None:
            raise AgentPolicyError("Research Director is not active")
        if worker_count > director.max_concurrency:
            raise AgentPolicyError("Worker count exceeds director concurrency budget")
        delegation_id = str(uuid4())
        shards = [items[index::worker_count] for index in range(worker_count)]
        workers: list[AgentRecord] = []
        assignments: list[AgentAssignmentRecord] = []
        for index, shard in enumerate(shards, start=1):
            worker = await self.create_agent(
                name=f"Research Worker {index}", template_name=template_name, parent_id=director.id
            )
            workers.append(worker)
            assignments.append(
                await self.repository.create_assignment(
                    delegation_id,
                    worker.id,
                    objective,
                    shard,
                    {**(context or {}), "data_classification": "simulation"},
                )
            )
        await self.events.publish(
            RuntimeEvent(
                "delegation.started",
                None,
                {
                    "delegation_id": delegation_id,
                    "worker_count": worker_count,
                    "item_count": len(items),
                },
            )
        )
        started = monotonic()
        tasks = [
            asyncio.create_task(self._execute_assignment(agent, assignment))
            for agent, assignment in zip(workers, assignments, strict=True)
        ]
        for worker, task in zip(workers, tasks, strict=True):
            self._running[worker.id] = task
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for worker in workers:
            self._running.pop(worker.id, None)
            current = await self.repository.get_agent(worker.id)
            if current and current.status != AgentStatus.TERMINATED:
                await self.terminate_agent(worker.id)
        failures = [result for result in results if isinstance(result, BaseException)]
        completed = [result for result in results if isinstance(result, AgentAssignmentRecord)]
        comparisons: list[dict[str, Any]] = []
        evidence: list[str] = []
        uncertainty: list[str] = []
        total_cost = 0
        for assignment in completed:
            comparisons.extend((assignment.result or {}).get("comparisons", []))
            evidence.extend(assignment.evidence)
            uncertainty.extend(assignment.uncertainty)
            total_cost += assignment.cost_units
        order = {item: index for index, item in enumerate(items)}
        comparisons.sort(key=lambda item: order.get(str(item.get("competitor")), len(order)))
        status = "success" if not failures else ("partial_success" if completed else "failed")
        result = {
            "delegation_id": delegation_id,
            "status": status,
            "objective": objective,
            "workers": [worker.id for worker in workers],
            "comparisons": comparisons,
            "evidence": evidence,
            "confidence": min((assignment.confidence or 0 for assignment in completed), default=0),
            "uncertainty": sorted(set(uncertainty)),
            "cost_units": total_cost,
            "runtime_ms": round((monotonic() - started) * 1000),
            "data_classification": "simulation",
        }
        await self.events.publish(
            RuntimeEvent(
                "delegation.completed",
                None,
                {
                    "delegation_id": delegation_id,
                    "status": status,
                    "worker_count": worker_count,
                    "cost_units": total_cost,
                },
            )
        )
        return result

    async def _execute_assignment(
        self, agent: AgentRecord, record: AgentAssignmentRecord
    ) -> AgentAssignmentRecord:
        if agent.status != AgentStatus.ACTIVE:
            raise AgentPolicyError("Agent is not active")
        await self.repository.update_assignment(
            record.id, status=AssignmentStatus.RUNNING, started_at=datetime.now(UTC)
        )
        await self.events.publish(
            RuntimeEvent(
                "agent.assignment.started", None, {"agent_id": agent.id, "assignment_id": record.id}
            )
        )
        try:
            async with self._semaphore, asyncio.timeout(agent.max_runtime_seconds):
                result = await self.executor.execute(
                    WorkerAssignment(
                        record.id, agent.id, record.objective, tuple(record.items), record.context
                    )
                )
            if result.cost_units > agent.max_cost_units:
                raise AgentPolicyError("Worker exceeded its cost budget")
            completed = await self.repository.update_assignment(
                record.id,
                status=AssignmentStatus.SUCCESS,
                result=result.output,
                evidence=result.evidence,
                confidence=result.confidence,
                uncertainty=result.uncertainty,
                cost_units=result.cost_units,
                finished_at=datetime.now(UTC),
            )
            await self.send_message(
                agent.id,
                agent.parent_id or agent.id,
                "assignment.result",
                {"assignment_id": record.id, **asdict(result)},
                record.id,
            )
            await self.events.publish(
                RuntimeEvent(
                    "agent.assignment.completed",
                    None,
                    {
                        "agent_id": agent.id,
                        "assignment_id": record.id,
                        "cost_units": result.cost_units,
                    },
                )
            )
            return completed
        except asyncio.CancelledError:
            await self.repository.update_assignment(
                record.id,
                status=AssignmentStatus.CANCELLED,
                error="Agent terminated",
                finished_at=datetime.now(UTC),
            )
            raise
        except Exception as exc:
            await self.repository.update_assignment(
                record.id,
                status=AssignmentStatus.FAILED,
                error=str(exc),
                finished_at=datetime.now(UTC),
            )
            await self.events.publish(
                RuntimeEvent(
                    "agent.assignment.failed",
                    None,
                    {"agent_id": agent.id, "assignment_id": record.id, "error": str(exc)},
                )
            )
            raise

    async def _require_agent(self, agent_id: str) -> AgentRecord:
        agent = await self.repository.get_agent(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        return agent

    async def _require_mutable_agent(self, agent_id: str) -> AgentRecord:
        agent = await self._require_agent(agent_id)
        if agent.kind != AgentKind.TEMPORARY:
            raise AgentPolicyError("Permanent agents cannot be modified")
        if agent.status == AgentStatus.TERMINATED:
            raise AgentPolicyError("Agent is terminated")
        return agent

    async def shutdown(self) -> None:
        tasks = [task for task in self._running.values() if not task.done()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._running.clear()
