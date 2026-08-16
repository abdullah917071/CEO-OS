"""Data contracts for Garry Tan's gstack virtual engineering team subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class GstackRole(StrEnum):
    OFFICE_HOURS = "office_hours"
    PLAN_CEO = "plan_ceo_review"
    PLAN_ENG = "plan_eng_review"
    DESIGN_REVIEW = "design_review"
    STAFF_REVIEW = "staff_review"
    QA_ENGINEER = "qa_engineer"
    RELEASE_SHIP = "release_ship"
    REFLECT = "reflect"


class GstackPhase(StrEnum):
    THINK = "think"
    PLAN = "plan"
    BUILD = "build"
    REVIEW = "review"
    TEST = "test"
    SHIP = "ship"
    REFLECT = "reflect"


@dataclass(frozen=True, slots=True)
class OfficeHoursReport:
    problem_statement: str
    target_customer: str
    hair_on_fire_pain: str
    key_assumptions: list[str]
    forcing_questions: list[str]
    ten_star_experience: str
    verdict: str
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class CeoReviewReport:
    product_scope: str
    killer_feature: str
    scope_cuts: list[str]
    strategic_differentiation: str
    verdict: str
    reviewed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class EngReviewReport:
    architecture_summary: str
    data_model_risks: list[str]
    concurrency_risks: list[str]
    failure_modes: list[str]
    architectural_guardrails: list[str]
    verdict: str
    reviewed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class DesignReviewReport:
    ux_heuristic_score: int
    anti_ai_slop_checks: list[str]
    layout_hierarchy_feedback: str
    micro_interactions: list[str]
    verdict: str
    reviewed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class StaffReviewReport:
    files_reviewed: list[str]
    critical_bugs_found: list[str]
    race_conditions: list[str]
    security_risks: list[str]
    performance_hotspots: list[str]
    verdict: str
    reviewed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class QaReport:
    browser_checks: list[str]
    routes_tested: list[str]
    ui_errors: list[str]
    regressions_detected: list[str]
    visual_evidence: list[str]
    verdict: str
    tested_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class ShipReport:
    git_branch: str
    checks_passed: list[str]
    commit_summary: str
    pr_title: str
    pr_body: str
    ship_status: str
    shipped_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class GstackPipelineRun:
    run_id: str
    task_id: str
    objective: str
    current_phase: GstackPhase
    office_hours: OfficeHoursReport | None = None
    ceo_review: CeoReviewReport | None = None
    eng_review: EngReviewReport | None = None
    staff_review: StaffReviewReport | None = None
    qa: QaReport | None = None
    ship: ShipReport | None = None
    status: str = "COMPLETED"
    total_duration_ms: float = 0.0
