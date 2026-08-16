from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class AgentKind(StrEnum):
    PERMANENT = "permanent"
    TEMPORARY = "temporary"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


class AssignmentStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AgentBudget:
    max_runtime_seconds: int
    max_cost_units: int
    max_concurrency: int


@dataclass(frozen=True, slots=True)
class AgentTemplate:
    name: str
    version: int
    role: str
    allowed_capabilities: frozenset[str]
    data_scope: frozenset[str]
    model_class: str
    can_spawn_agents: bool
    budget: AgentBudget


@dataclass(frozen=True, slots=True)
class WorkerAssignment:
    assignment_id: str
    agent_id: str
    objective: str
    items: tuple[str, ...]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkerResult:
    output: dict[str, Any]
    evidence: list[str]
    confidence: float
    uncertainty: list[str]
    cost_units: int


class WorkerExecutor(Protocol):
    async def execute(self, assignment: WorkerAssignment) -> WorkerResult: ...
