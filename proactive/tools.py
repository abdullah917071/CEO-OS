from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from proactive.engine import ProactiveCeoEngine


class ProactiveEvaluateTool:
    """Tool to run an evaluation pass over all business triggers and generate proactive insights."""

    def __init__(self, engine: ProactiveCeoEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="proactive.evaluate",
            description="Evaluate active business event triggers and generate proactive insights",
            input_schema={
                "type": "object",
                "properties": {
                    "metrics_override": {
                        "type": "object",
                        "description": "Optional telemetry metrics override for simulation testing",
                    }
                },
            },
            risk=RiskLevel.READ,
            source="integration:proactive_ceo",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        overrides = arguments.get("metrics_override")
        if isinstance(overrides, dict):
            metric_overrides = {str(k): float(v) for k, v in overrides.items()}
        else:
            metric_overrides = None

        report = self._engine.evaluate_business_state(metric_overrides)
        t_count = report.triggers_evaluated_count
        g_count = report.goals_tracked_count
        f_count = report.triggers_fired_count
        i_count = report.active_insights_count
        evidence = [
            f"Evaluated {t_count} triggers across {g_count} goals",
            f"Fired {f_count} trigger(s), generated {i_count} insight(s)",
        ]
        for ins in report.insights:
            evidence.append(f"[{ins.severity.upper()}] {ins.title}: {ins.observation}")

        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=evidence,
        )


class ProactiveInsightsGetTool:
    """Tool to retrieve active prioritized proactive insights and recommendations."""

    def __init__(self, engine: ProactiveCeoEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="proactive.insights.get",
            description="Retrieve prioritized proactive observations and recommended interventions",
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.READ,
            source="integration:proactive_ceo",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        insights = self._engine.get_active_insights()
        if not insights:
            # If empty, run an evaluation pass first
            report = self._engine.evaluate_business_state()
            insights = report.insights

        evidence = [
            f"Retrieved {len(insights)} active proactive insight(s)",
        ]
        for ins in insights:
            evidence.append(f"{ins.title} -> {ins.recommended_action}")

        return ToolResult(
            output={"insights": [dataclasses.asdict(i) for i in insights], "count": len(insights)},
            evidence=evidence,
        )


class ProactiveTriggerCreateTool:
    """Tool to create and register a custom business event trigger."""

    def __init__(self, engine: ProactiveCeoEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="proactive.trigger.create",
            description="Create a proactive event trigger to continuously monitor business metrics",
            input_schema={
                "type": "object",
                "required": [
                    "name",
                    "description",
                    "category",
                    "metric_key",
                    "operator",
                    "threshold",
                ],
                "properties": {
                    "name": {"type": "string", "description": "Trigger name"},
                    "description": {"type": "string", "description": "Trigger description"},
                    "category": {
                        "type": "string",
                        "enum": ["finance", "marketing", "sales", "operations", "system"],
                    },
                    "metric_key": {"type": "string", "description": "Telemetry metric key"},
                    "operator": {
                        "type": "string",
                        "enum": ["<", "<=", ">", ">=", "==", "!=", "pct_change_gt"],
                    },
                    "threshold": {"type": "number", "description": "Numerical trigger threshold"},
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "critical"],
                        "default": "warning",
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:proactive_ceo",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        trigger = self._engine.create_trigger(
            name=str(arguments["name"]),
            description=str(arguments["description"]),
            category=str(arguments["category"]),
            metric_key=str(arguments["metric_key"]),
            operator=str(arguments["operator"]),
            threshold=float(arguments["threshold"]),
            severity=str(arguments.get("severity", "warning")),
        )

        cond = trigger.condition
        return ToolResult(
            output=dataclasses.asdict(trigger),
            evidence=[
                f"Created trigger '{trigger.name}' [{trigger.category}] on "
                f"{cond.metric_key} {cond.operator} {cond.threshold}",
            ],
        )


class ProactiveTriggerListTool:
    """Tool to list registered business event triggers."""

    def __init__(self, engine: ProactiveCeoEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="proactive.trigger.list",
            description="List configured proactive event triggers and firing metrics",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Optional category filter"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:proactive_ceo",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        category = arguments.get("category")
        triggers = self._engine.list_triggers(category=category)

        return ToolResult(
            output={"triggers": [dataclasses.asdict(t) for t in triggers], "count": len(triggers)},
            evidence=[f"Listed {len(triggers)} configured proactive trigger(s)"],
        )


class ProactiveGoalCreateTool:
    """Tool to create a strategic goal tree with milestone tracking."""

    def __init__(self, engine: ProactiveCeoEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="proactive.goal.create",
            description="Create a strategic business goal tree with target milestones",
            input_schema={
                "type": "object",
                "required": ["title", "description", "category", "target_date"],
                "properties": {
                    "title": {"type": "string", "description": "Goal title"},
                    "description": {"type": "string", "description": "Goal description"},
                    "category": {
                        "type": "string",
                        "enum": ["finance", "marketing", "sales", "operations", "system"],
                    },
                    "target_date": {
                        "type": "string",
                        "description": "ISO target completion date (YYYY-MM-DD)",
                    },
                    "milestones": {
                        "type": "array",
                        "description": "List of key milestone targets",
                        "items": {"type": "object"},
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:proactive_ceo",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        goal = self._engine.create_goal(
            title=str(arguments["title"]),
            description=str(arguments["description"]),
            category=str(arguments["category"]),
            target_date=str(arguments["target_date"]),
            milestones=arguments.get("milestones"),
        )

        return ToolResult(
            output=dataclasses.asdict(goal),
            evidence=[
                f"Created goal '{goal.title}' [Target: {goal.target_date}] "
                f"with {len(goal.milestones)} milestone(s)",
            ],
        )


class ProactiveGoalListTool:
    """Tool to list active strategic goal trees and progression."""

    def __init__(self, engine: ProactiveCeoEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="proactive.goal.list",
            description="List active strategic goals, target dates, and progress percentage",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Optional category filter"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:proactive_ceo",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        category = arguments.get("category")
        goals = self._engine.list_goals(category=category)

        return ToolResult(
            output={"goals": [dataclasses.asdict(g) for g in goals], "count": len(goals)},
            evidence=[f"Listed {len(goals)} active strategic goal(s)"],
        )
