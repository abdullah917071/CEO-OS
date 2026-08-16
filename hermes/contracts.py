"""Data contracts for the Nous Hermes Agent subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class HermesRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class HermesToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str = field(default_factory=lambda: f"call_{uuid4().hex[:8]}")


@dataclass(frozen=True, slots=True)
class HermesToolResponse:
    name: str
    output: Any
    evidence: list[str] = field(default_factory=list)
    error: str | None = None
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class HermesMessage:
    role: HermesRole
    content: str
    thought: str | None = None
    tool_calls: list[HermesToolCall] = field(default_factory=list)
    tool_response: HermesToolResponse | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class HermesTrajectoryStep:
    step_index: int
    thought: str
    tool_call: HermesToolCall | None = None
    tool_response: HermesToolResponse | None = None
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class HermesTrajectoryRecord:
    trajectory_id: str
    task_id: str
    objective: str
    system_prompt: str
    steps: list[HermesTrajectoryStep]
    final_response: str
    total_duration_ms: float
    status: str
    recorded_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class HermesSynthesizedSkill:
    name: str
    description: str
    content_markdown: str
    source_trajectory_id: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class HermesReflectionResult:
    reflection_id: str
    trajectory_id: str
    insights: list[str]
    lessons_learned: list[str]
    synthesized_skill: HermesSynthesizedSkill | None = None
    evaluated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class HermesSubagentSpec:
    subagent_id: str
    role: str
    objective: str
    allowed_capabilities: list[str] = field(default_factory=list)
    parent_id: str | None = None
    max_turns: int = 5


@dataclass(frozen=True, slots=True)
class HermesSubagentResult:
    subagent_id: str
    objective: str
    status: str
    output: str
    evidence: list[str]
    duration_ms: float


@dataclass(frozen=True, slots=True)
class HermesRunResult:
    run_id: str
    task_id: str
    objective: str
    status: str
    thought: str
    final_answer: str
    trajectory: HermesTrajectoryRecord
    reflection: HermesReflectionResult | None
    evidence: list[str]
    duration_ms: float
