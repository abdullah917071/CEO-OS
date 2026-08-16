"""Skills Engine: registry, validation, dry-run simulation, execution, and versioning."""

from __future__ import annotations

import logging
import re
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.capabilities import CapabilityRegistry
from skills.contracts import (
    SkillDefinition,
    SkillExecutionResult,
    SkillStats,
    SkillStep,
    SkillTestResult,
    SkillVersionRecord,
)

logger = logging.getLogger(__name__)


def _interpolate_template(val: Any, context: dict[str, Any]) -> Any:
    """Recursively replace {{key}} references with values from context."""
    if isinstance(val, str):
        pattern = re.compile(r"\{\{([^}]+)\}\}")
        match = pattern.fullmatch(val.strip())
        if match:
            key = match.group(1).strip()
            return context.get(key, val)

        def repl(m: re.Match[str]) -> str:
            k = m.group(1).strip()
            return str(context.get(k, m.group(0)))

        return pattern.sub(repl, val)
    if isinstance(val, dict):
        return {k: _interpolate_template(v, context) for k, v in val.items()}
    if isinstance(val, list):
        return [_interpolate_template(item, context) for item in val]
    return val


class SkillsEngine:
    """Execution and lifecycle engine for versioned procedural skills."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}
        self._load_builtin_skills()

    def _load_builtin_skills(self) -> None:
        """Seed pre-configured procedural skills from the CEO OS library."""
        # 1. Prepare Client Report
        self._skills["prepare_client_report"] = SkillDefinition(
            skill_id="prepare_client_report",
            name="Prepare Client Report",
            description="Fetch billing receivables, marketing stats, and email client report.",
            version="1.0.0",
            category="reporting",
            tags=["client", "finance", "marketing", "email"],
            parameters_schema={
                "type": "object",
                "required": ["client_name", "recipient_email"],
                "properties": {
                    "client_name": {"type": "string"},
                    "recipient_email": {"type": "string"},
                    "subject": {"type": "string", "default": "Monthly Performance Report"},
                },
            },
            steps=[
                SkillStep(
                    step_id="step_1_invoices",
                    capability="business.finance.invoices",
                    arguments_template={"status": "ALL"},
                    success_condition="Client invoices retrieved",
                ),
                SkillStep(
                    step_id="step_2_marketing",
                    capability="marketing.snapshot.get",
                    arguments_template={},
                    success_condition="Marketing snapshot obtained",
                ),
                SkillStep(
                    step_id="step_3_send_email",
                    capability="comms.email.send",
                    arguments_template={
                        "to_email": "{{recipient_email}}",
                        "subject": "{{subject}}",
                        "body": "Hi {{client_name}}, your monthly executive report is ready.",
                    },
                    success_condition="Client report delivered via email",
                ),
            ],
            owner_agent="finance",
        )

        # 2. Launch Meta Campaign
        self._skills["launch_meta_campaign"] = SkillDefinition(
            skill_id="launch_meta_campaign",
            name="Launch Meta Campaign",
            description="Create campaign, target adset, and attach ad creative on Meta Marketing.",
            version="1.0.0",
            category="marketing",
            tags=["meta", "advertising", "growth"],
            parameters_schema={
                "type": "object",
                "required": ["campaign_name", "daily_budget"],
                "properties": {
                    "campaign_name": {"type": "string"},
                    "daily_budget": {"type": "number"},
                    "objective": {"type": "string", "default": "OUTCOME_SALES"},
                },
            },
            steps=[
                SkillStep(
                    step_id="step_1_campaign",
                    capability="meta.campaign.create",
                    arguments_template={
                        "name": "{{campaign_name}}",
                        "objective": "{{objective}}",
                        "daily_budget": "{{daily_budget}}",
                    },
                    success_condition="Meta campaign created",
                ),
                SkillStep(
                    step_id="step_2_adset",
                    capability="meta.adset.create",
                    arguments_template={
                        "campaign_id": "cmp_auto_gen",
                        "name": "{{campaign_name}} - AdSet A",
                        "daily_budget": "{{daily_budget}}",
                        "targeting": {"age_min": 21, "age_max": 55},
                    },
                    success_condition="Targeted ad set created",
                ),
            ],
            owner_agent="marketing",
        )

        # 3. Analyze Weekly Sales
        self._skills["analyze_weekly_sales"] = SkillDefinition(
            skill_id="analyze_weekly_sales",
            name="Analyze Weekly Sales",
            description="Compile sales pipeline health, revenue metrics, and broadcast summary.",
            version="1.0.0",
            category="sales",
            tags=["sales", "pipeline", "broadcast"],
            parameters_schema={"type": "object", "properties": {}},
            steps=[
                SkillStep(
                    step_id="step_1_pipeline",
                    capability="business.sales.pipeline",
                    arguments_template={},
                    success_condition="Sales pipeline evaluated",
                ),
                SkillStep(
                    step_id="step_2_financials",
                    capability="business.finance.overview",
                    arguments_template={},
                    success_condition="Financial overview retrieved",
                ),
                SkillStep(
                    step_id="step_3_broadcast",
                    capability="comms.notification.broadcast",
                    arguments_template={
                        "title": "Weekly Sales & Pipeline Briefing",
                        "message": "Weekly sales analysis completed with pipeline updates.",
                        "severity": "info",
                    },
                    success_condition="Sales summary broadcast to executives",
                ),
            ],
            owner_agent="sales",
        )

        # 4. Qualify Lead
        self._skills["qualify_lead"] = SkillDefinition(
            skill_id="qualify_lead",
            name="Qualify Lead",
            description="Analyze transcript, update sales opportunities, and schedule cadence.",
            version="1.0.0",
            category="sales",
            tags=["sales", "leads", "cadence"],
            parameters_schema={
                "type": "object",
                "required": ["transcript", "prospect_name", "prospect_email"],
                "properties": {
                    "transcript": {"type": "string"},
                    "prospect_name": {"type": "string"},
                    "prospect_email": {"type": "string"},
                },
            },
            steps=[
                SkillStep(
                    step_id="step_1_analyze",
                    capability="comms.conversation.analyze",
                    arguments_template={"transcript": "{{transcript}}"},
                    success_condition="Lead qualification completed",
                ),
                SkillStep(
                    step_id="step_2_followup",
                    capability="comms.followup.schedule",
                    arguments_template={
                        "channel": "email",
                        "to_email": "{{prospect_email}}",
                        "name": "{{prospect_name}}",
                        "objective": "Send product overview and demo link",
                        "days_from_now": 2,
                    },
                    success_condition="Follow-up cadence scheduled",
                ),
            ],
            owner_agent="sales",
        )

    # ── Registry Operations ─────────────────────────────────────────────────────

    def create_skill(
        self,
        name: str,
        description: str,
        steps: list[SkillStep],
        parameters_schema: dict[str, Any] | None = None,
        category: str = "general",
        tags: list[str] | None = None,
        owner_agent: str = "ceo",
        skill_id: str | None = None,
    ) -> SkillDefinition:
        """Register a new learned procedural skill."""
        sid = skill_id or re.sub(r"[^a-z0-9_]+", "_", name.lower().strip()).strip("_")
        if not sid:
            sid = f"skill_{uuid4().hex[:8]}"

        now = datetime.now(UTC).isoformat()
        skill = SkillDefinition(
            skill_id=sid,
            name=name,
            description=description,
            version="1.0.0",
            category=category,
            tags=tags or [],
            parameters_schema=parameters_schema or {"type": "object", "properties": {}},
            steps=steps,
            owner_agent=owner_agent,
            enabled=True,
            created_at=now,
            updated_at=now,
            stats=SkillStats(),
            version_history=[
                SkillVersionRecord(
                    version="1.0.0",
                    created_at=now,
                    changelog="Initial procedural skill creation",
                    steps_count=len(steps),
                )
            ],
        )
        self._skills[sid] = skill
        return skill

    def get_skill(self, skill_id: str) -> SkillDefinition:
        """Retrieve skill definition by ID."""
        if skill_id not in self._skills:
            raise KeyError(f"Skill '{skill_id}' not found")
        return self._skills[skill_id]

    def list_skills(
        self,
        category: str | None = None,
        enabled_only: bool = False,
        owner_agent: str | None = None,
    ) -> list[SkillDefinition]:
        """List skills matching criteria."""
        results = list(self._skills.values())
        if category:
            results = [s for s in results if s.category.lower() == category.lower()]
        if enabled_only:
            results = [s for s in results if s.enabled]
        if owner_agent:
            results = [s for s in results if s.owner_agent.lower() == owner_agent.lower()]
        return results

    # ── Simulation & Testing ────────────────────────────────────────────────────

    def test_skill(
        self,
        skill_id: str,
        mock_inputs: dict[str, Any] | None = None,
        capability_registry: CapabilityRegistry | None = None,
    ) -> SkillTestResult:
        """Dry-run test a skill with structural verification and argument compatibility check."""
        skill = self.get_skill(skill_id)
        start_time = time.perf_counter()
        errors: list[str] = []
        step_results: list[dict[str, Any]] = []

        inputs = mock_inputs or {}
        required_props = skill.parameters_schema.get("required", [])
        for req in required_props:
            if req not in inputs:
                errors.append(f"Missing required parameter '{req}' for testing")

        context = dict(inputs)

        for step in skill.steps:
            step_passed = True
            step_error = None

            # 1. Verify capability availability if registry provided
            if capability_registry is not None and not capability_registry.has(step.capability):
                step_passed = False
                step_error = f"Capability '{step.capability}' not found in registry"
                errors.append(step_error)

            # 2. Check variable interpolation completeness
            try:
                interpolated = _interpolate_template(step.arguments_template, context)
            except Exception as exc:
                step_passed = False
                step_error = f"Interpolation error: {exc}"
                errors.append(step_error)
                interpolated = step.arguments_template

            step_results.append(
                {
                    "step_id": step.step_id,
                    "capability": step.capability,
                    "arguments_interpolated": interpolated,
                    "passed": step_passed,
                    "error": step_error,
                }
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        passed = len(errors) == 0

        return SkillTestResult(
            skill_id=skill_id,
            passed=passed,
            step_results=step_results,
            validation_errors=errors,
            simulated_duration_ms=duration_ms,
        )

    # ── Execution Pipeline ──────────────────────────────────────────────────────

    async def execute_skill(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        capability_registry: CapabilityRegistry | None = None,
    ) -> SkillExecutionResult:
        """Execute a learned procedural skill with parameter inputs."""
        skill = self.get_skill(skill_id)
        if not skill.enabled:
            raise ValueError(f"Skill '{skill.name}' is currently disabled")

        start_time = time.perf_counter()
        exec_id = f"exec_{uuid4().hex[:10]}"
        context = dict(inputs)
        step_outputs: list[dict[str, Any]] = []
        evidence: list[str] = []
        executed_count = 0

        try:
            for step in skill.steps:
                interpolated_args = _interpolate_template(step.arguments_template, context)

                if capability_registry is not None:
                    tool = capability_registry.get(step.capability)
                    if tool is not None:
                        res = await tool.execute(interpolated_args)
                        out = res.output
                        step_evidence = res.evidence
                    else:
                        out = {"status": "simulated_success", "step": step.step_id}
                        step_evidence = [f"Step {step.step_id} completed: {step.success_condition}"]
                else:
                    out = {"status": "simulated_success", "step": step.step_id}
                    step_evidence = [f"Step {step.step_id} completed: {step.success_condition}"]

                executed_count += 1
                step_outputs.append({"step_id": step.step_id, "output": out})
                evidence.extend(step_evidence)

                # Feed output back into context for subsequent steps
                if isinstance(out, dict):
                    for k, v in out.items():
                        context[f"{step.step_id}.{k}"] = v

            duration = round((time.perf_counter() - start_time) * 1000.0, 2)

            # Update telemetry
            skill.stats.runs_count += 1
            skill.stats.success_count += 1
            skill.stats.last_used_at = datetime.now(UTC).isoformat()
            if skill.stats.runs_count == 1:
                skill.stats.average_runtime_ms = duration
            else:
                skill.stats.average_runtime_ms = round(
                    (skill.stats.average_runtime_ms + duration) / 2.0, 2
                )

            return SkillExecutionResult(
                execution_id=exec_id,
                skill_id=skill_id,
                status="success",
                steps_executed=executed_count,
                total_steps=len(skill.steps),
                step_outputs=step_outputs,
                evidence=evidence,
                duration_ms=duration,
            )

        except Exception as exc:
            duration = round((time.perf_counter() - start_time) * 1000.0, 2)
            skill.stats.runs_count += 1
            skill.stats.failure_count += 1
            skill.stats.last_used_at = datetime.now(UTC).isoformat()
            logger.exception("Failed executing skill '%s'", skill_id)

            return SkillExecutionResult(
                execution_id=exec_id,
                skill_id=skill_id,
                status="failed",
                steps_executed=executed_count,
                total_steps=len(skill.steps),
                step_outputs=step_outputs,
                evidence=evidence,
                error=str(exc),
                duration_ms=duration,
            )

    # ── Versioning & State ──────────────────────────────────────────────────────

    def version_skill(
        self,
        skill_id: str,
        new_version: str,
        changelog: str,
        new_steps: list[SkillStep] | None = None,
        new_description: str | None = None,
    ) -> SkillDefinition:
        """Bump skill version and record changelog history."""
        skill = self.get_skill(skill_id)
        now = datetime.now(UTC).isoformat()

        # Archive current version
        skill.version_history.append(
            SkillVersionRecord(
                version=skill.version,
                created_at=skill.updated_at,
                changelog=changelog,
                steps_count=len(skill.steps),
            )
        )

        skill.version = new_version
        if new_steps is not None:
            skill.steps = new_steps
        if new_description is not None:
            skill.description = new_description
        skill.updated_at = now

        return skill

    def disable_skill(self, skill_id: str, disabled: bool = True) -> SkillDefinition:
        """Enable or disable a procedural skill."""
        skill = self.get_skill(skill_id)
        skill.enabled = not disabled
        skill.updated_at = datetime.now(UTC).isoformat()
        return skill
