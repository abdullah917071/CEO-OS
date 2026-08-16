"""Data contracts for the CEO OS Executive AI Agent and ReAct Reasoning Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CeoRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class CeoToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class CeoToolResponse:
    name: str
    output: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    error: str | None = None
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class CeoMessage:
    role: CeoRole
    content: str
    thought: str | None = None
    tool_calls: list[CeoToolCall] = field(default_factory=list)
    tool_response: CeoToolResponse | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class CeoTrajectoryStep:
    step_index: int
    thought: str
    tool_call: CeoToolCall | None = None
    tool_response: CeoToolResponse | None = None
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class CeoTrajectoryRecord:
    trajectory_id: str
    task_id: str
    objective: str
    system_prompt: str
    steps: list[CeoTrajectoryStep]
    final_response: str
    total_duration_ms: float
    status: str
    recorded_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class CeoSynthesizedSkill:
    name: str
    description: str
    content_markdown: str
    source_trajectory_id: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class CeoReflectionResult:
    reflection_id: str
    trajectory_id: str
    insights: list[str]
    lessons_learned: list[str]
    synthesized_skill: CeoSynthesizedSkill | None = None
    evaluated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class CeoSubagentSpec:
    subagent_id: str
    role: str
    objective: str
    allowed_capabilities: list[str] = field(default_factory=list)
    parent_id: str | None = None
    max_turns: int = 5


@dataclass(frozen=True, slots=True)
class CeoSubagentResult:
    subagent_id: str
    objective: str
    status: str
    output: str
    evidence: list[str]
    duration_ms: float


@dataclass(frozen=True, slots=True)
class CeoRunResult:
    run_id: str
    task_id: str
    objective: str
    status: str
    thought: str
    final_answer: str
    trajectory: CeoTrajectoryRecord
    reflection: CeoReflectionResult | None
    evidence: list[str]
    duration_ms: float


# Backwards compatibility aliases
HermesRole = CeoRole
HermesToolCall = CeoToolCall
HermesToolResponse = CeoToolResponse
HermesMessage = CeoMessage
HermesTrajectoryStep = CeoTrajectoryStep
HermesTrajectoryRecord = CeoTrajectoryRecord
HermesSynthesizedSkill = CeoSynthesizedSkill
HermesReflectionResult = CeoReflectionResult
HermesSubagentSpec = CeoSubagentSpec
HermesSubagentResult = CeoSubagentResult
HermesRunResult = CeoRunResult
