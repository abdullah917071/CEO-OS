"""Contracts and data schemas for the versioned procedural Skills Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SkillStep:
    """An individual atomic step inside a procedural skill."""

    step_id: str
    capability: str
    arguments_template: dict[str, Any]
    success_condition: str
    timeout_seconds: float = 30.0
    optional: bool = False


@dataclass(slots=True)
class SkillStats:
    """Execution telemetry and reliability metrics for a skill."""

    runs_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_runtime_ms: float = 0.0
    last_used_at: str | None = None

    @property
    def success_rate(self) -> float:
        if self.runs_count == 0:
            return 100.0
        return round((self.success_count / self.runs_count) * 100.0, 1)


@dataclass(frozen=True, slots=True)
class SkillVersionRecord:
    """Historical version entry with changelog."""

    version: str
    created_at: str
    changelog: str
    steps_count: int


@dataclass(slots=True)
class SkillDefinition:
    """Comprehensive specification of a learned procedural skill."""

    skill_id: str
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    steps: list[SkillStep] = field(default_factory=list)
    owner_agent: str = "ceo"
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    stats: SkillStats = field(default_factory=SkillStats)
    version_history: list[SkillVersionRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SkillTestResult:
    """Dry-run simulation and structural verification outcome."""

    skill_id: str
    passed: bool
    step_results: list[dict[str, Any]]
    validation_errors: list[str] = field(default_factory=list)
    simulated_duration_ms: float = 0.0
    tested_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class SkillExecutionResult:
    """Outcome of running a skill procedure."""

    execution_id: str
    skill_id: str
    status: str
    steps_executed: int
    total_steps: int
    step_outputs: list[dict[str, Any]]
    evidence: list[str]
    error: str | None = None
    duration_ms: float = 0.0
    executed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
