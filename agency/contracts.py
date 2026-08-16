"""Contracts and data models for the Agency Agents subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AgencyDomain(StrEnum):
    """Broad domain classification for agency skills."""

    ENGINEERING = "engineering"
    FINOPS_FINANCE = "finops_finance"
    MARKETING_GROWTH = "marketing_growth"
    SALES_DEAL = "sales_deal"
    OPERATIONS_PM = "operations_pm"
    SECURITY_QA = "security_qa"
    GEOSPATIAL_3D = "geospatial_3d"
    CREATIVE_CONTENT = "creative_content"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class AgencySkillPersona:
    """Comprehensive definition and persona of an Agency Agent skill."""

    name: str
    description: str
    role: str
    domain: AgencyDomain
    tags: list[str] = field(default_factory=list)
    personality: str = ""
    core_mission: list[str] = field(default_factory=list)
    critical_rules: list[str] = field(default_factory=list)
    workflow_phases: list[str] = field(default_factory=list)
    allowed_capabilities: list[str] = field(default_factory=list)
    raw_content: str = ""
    file_path: str = ""


@dataclass(frozen=True, slots=True)
class SkillMatchScore:
    """Match result representing how relevant an agency skill is to a task."""

    skill_name: str
    domain: AgencyDomain
    relevance_score: float
    matched_keywords: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class AgencyMatchResult:
    """Aggregated ranking response for task skill matching."""

    query: str
    matches: list[SkillMatchScore]
    best_match: SkillMatchScore | None = None
    total_skills_evaluated: int = 0
    matched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class AgencyExecutionPlan:
    """Skill-guided execution plan for an autonomous task."""

    task_id: str
    objective: str
    matched_skill: AgencySkillPersona
    guidance_prompt: str
    quality_gates: list[str]
    suggested_capabilities: list[str]
    planned_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class AgencyExecutionResult:
    """Result of running a task with Agency Agent skill guidance."""

    execution_id: str
    task_id: str
    skill_name: str
    status: str
    output: dict[str, Any]
    evidence: list[str]
    quality_checks_passed: list[str]
    confidence: float = 1.0
    duration_ms: float = 0.0
    executed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
