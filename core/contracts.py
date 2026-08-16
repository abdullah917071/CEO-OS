from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID


class RiskLevel(StrEnum):
    READ = "R0"
    HARMLESS_WRITE = "R1"
    EXTERNAL_COMMUNICATION = "R2"
    BUSINESS_CHANGE = "R3"
    DESTRUCTIVE_ADMIN = "R4"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    RETRYING = "retrying"
    NEEDS_APPROVAL = "needs_approval"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskControl(StrEnum):
    RUN = "run"
    PAUSE = "pause"
    CANCEL = "cancel"


class StepStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: RiskLevel
    source: str = "internal"


@dataclass(frozen=True, slots=True)
class ToolResult:
    output: dict[str, Any] | list[Any]
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PlanStep:
    capability: str
    arguments: dict[str, Any]
    success_condition: str


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    objective: str
    success_conditions: list[str]
    steps: list[PlanStep]


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    event_type: str
    task_id: UUID | None
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class Tool(Protocol):
    @property
    def spec(self) -> CapabilitySpec: ...

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult: ...


class ModelProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def plan(self, message: str, capabilities: list[CapabilitySpec]) -> ExecutionPlan: ...


class EventPublisher(Protocol):
    async def publish(self, event: RuntimeEvent) -> None: ...


class EpisodeRecorder(Protocol):
    async def record_task_episode(
        self, task_id: UUID, objective: str, result: dict[str, Any]
    ) -> None: ...
