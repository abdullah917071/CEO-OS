"""Capability tools for Garry Tan's gstack virtual engineering team."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from gstack.engine import GstackEngine


class GstackOfficeHoursTool(Tool):
    """Tool for YC Partner Office Hours strategy forcing questions."""

    def __init__(self, engine: GstackEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="gstack.office_hours",
            description="Run YC partner office hours: challenge product assumptions",
            input_schema={
                "type": "object",
                "required": ["idea_or_spec"],
                "properties": {
                    "idea_or_spec": {"type": "string", "description": "Product idea"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:gstack",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        spec = str(arguments["idea_or_spec"])
        report = self._engine.run_office_hours(spec)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[
                f"Office hours completed for '{spec[:30]}...'",
                f"Verdict: {report.verdict}",
            ],
        )


class GstackCeoReviewTool(Tool):
    """Tool for CEO-level scope and killer feature review."""

    def __init__(self, engine: GstackEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="gstack.plan.ceo_review",
            description="Run CEO 10-star product strategy and scope review",
            input_schema={
                "type": "object",
                "required": ["plan_spec"],
                "properties": {
                    "plan_spec": {"type": "string", "description": "Plan specification text"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:gstack",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        plan = str(arguments["plan_spec"])
        report = self._engine.run_ceo_review(plan)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[
                f"CEO review completed: {report.verdict}",
                f"Killer feature: {report.killer_feature}",
            ],
        )


class GstackEngReviewTool(Tool):
    """Tool for Engineering Manager architecture guardrail review."""

    def __init__(self, engine: GstackEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="gstack.plan.eng_review",
            description="Run Engineering Manager architecture review and risk audit",
            input_schema={
                "type": "object",
                "required": ["arch_spec"],
                "properties": {
                    "arch_spec": {"type": "string", "description": "Architecture description"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:gstack",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        arch = str(arguments["arch_spec"])
        report = self._engine.run_eng_review(arch)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[
                f"Eng review completed: {report.verdict}",
                f"{len(report.architectural_guardrails)} guardrails verified",
            ],
        )


class GstackStaffReviewTool(Tool):
    """Tool for paranoid staff engineer code audit."""

    def __init__(self, engine: GstackEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="gstack.code.review",
            description="Run paranoid staff engineer code review for bugs and security",
            input_schema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files to review",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:gstack",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        files = arguments.get("files", [])
        report = self._engine.run_staff_review(files)
        files_count = len(report.files_reviewed)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[f"Staff review completed for {files_count} files: {report.verdict}"],
        )


class GstackQaBrowserTool(Tool):
    """Tool for QA Lead real browser verification."""

    def __init__(self, engine: GstackEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="gstack.qa.browser_test",
            description="Run route-aware browser QA and visual verification",
            input_schema={
                "type": "object",
                "properties": {
                    "routes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Routes to verify",
                    },
                    "base_url": {"type": "string", "default": "http://localhost:3000"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:gstack",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        routes = arguments.get("routes")
        base_url = arguments.get("base_url", "http://localhost:3000")
        report = await self._engine.run_qa(routes=routes, base_url=base_url)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=report.visual_evidence,
        )


class GstackReleaseShipTool(Tool):
    """Tool for release engineering shipping."""

    def __init__(self, engine: GstackEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="gstack.release.ship",
            description="Run release engineer validation, commit summary, and PR generation",
            input_schema={
                "type": "object",
                "properties": {
                    "branch": {"type": "string", "default": "main"},
                    "pr_title": {"type": "string"},
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:gstack",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        branch = str(arguments.get("branch", "main"))
        title = arguments.get("pr_title")
        report = self._engine.run_ship(git_branch=branch, pr_title=title)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[f"Ship status: {report.ship_status}", f"PR: {report.pr_title}"],
        )


class GstackPipelineRunTool(Tool):
    """Tool to execute complete 7-stage SDLC loop."""

    def __init__(self, engine: GstackEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="gstack.pipeline.run",
            description="Execute full 7-stage gstack virtual engineering SDLC pipeline",
            input_schema={
                "type": "object",
                "required": ["objective"],
                "properties": {
                    "objective": {"type": "string", "description": "Feature objective"},
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:gstack",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        obj = str(arguments["objective"])
        res = await self._engine.run_full_pipeline(obj)
        evidence = [
            f"gstack 7-stage pipeline completed in {res.total_duration_ms:.1f}ms",
            f"Think: {res.office_hours.verdict if res.office_hours else 'N/A'}",
            f"Plan: {res.ceo_review.verdict if res.ceo_review else 'N/A'}",
            f"Review: {res.staff_review.verdict if res.staff_review else 'N/A'}",
            f"Test: {res.qa.verdict if res.qa else 'N/A'}",
            f"Ship: {res.ship.ship_status if res.ship else 'N/A'}",
        ]
        return ToolResult(
            output=dataclasses.asdict(res),
            evidence=evidence,
        )
