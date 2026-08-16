"""Structured delegation protocol: task messages, constraints, and standardized deliverables."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskOutcomeStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"


@dataclass(slots=True)
class TaskConstraints:
    """Explicit guardrails and operational constraints for delegated work."""

    max_runtime_seconds: int = 1800
    max_cost_units: int = 100
    do_not_modify_production: bool = True
    dry_run_only: bool = False
    requires_approval_for_external_effects: bool = True
    allowed_domains: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StructuredTaskMessage:
    """Standardized input envelope for all delegated specialist assignments."""

    task_id: str
    objective: str
    target_agent_id: str
    deliverable: str  # e.g. "conversion_audit", "api_implementation", "threat_model"
    context_refs: list[str] = field(default_factory=list)  # e.g. ["repo:CEO-OS", "task:t_123"]
    constraints: TaskConstraints = field(default_factory=TaskConstraints)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StructuredTaskResult:
    """Standardized output envelope returned by all specialist executions."""

    task_id: str
    agent_id: str
    status: TaskOutcomeStatus
    summary: str
    findings: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.90
    cost_units: int = 1
    latency_ms: float = 200.0
    error: str | None = None
