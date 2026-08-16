from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from proactive.contracts import (
    EventTrigger,
    GoalMilestone,
    GoalStatus,
    GoalTree,
    ProactiveEvaluationReport,
    ProactiveInsight,
    TriggerCategory,
    TriggerCondition,
    TriggerSeverity,
)

logger = logging.getLogger(__name__)


class ProactiveCeoEngine:
    """Core proactive intelligence engine monitoring business telemetry, triggers, and goals."""

    def __init__(self) -> None:
        self._triggers: dict[str, EventTrigger] = {}
        self._goals: dict[str, GoalTree] = {}
        self._insights: list[ProactiveInsight] = []
        self._seed_builtin_triggers()
        self._seed_builtin_goals()

    def _seed_builtin_triggers(self) -> None:
        """Seed default high-leverage business event triggers."""
        builtins = [
            EventTrigger(
                id="trg_low_runway",
                name="Low Financial Runway Alert",
                description="Triggered when cash runway drops below 3.0 months.",
                category=TriggerCategory.FINANCE,
                condition=TriggerCondition(
                    metric_key="cash_runway_months",
                    operator="<",
                    threshold=3.0,
                ),
                severity=TriggerSeverity.CRITICAL,
                enabled=True,
            ),
            EventTrigger(
                id="trg_overdue_invoices",
                name="Overdue Invoices Warning",
                description="Triggered when unpaid overdue receivables exist.",
                category=TriggerCategory.FINANCE,
                condition=TriggerCondition(
                    metric_key="overdue_invoices_count",
                    operator=">",
                    threshold=0.0,
                ),
                severity=TriggerSeverity.WARNING,
                enabled=True,
            ),
            EventTrigger(
                id="trg_meta_cpa_fatigue",
                name="Meta Ad CPA Fatigue Alert",
                description="Triggered when campaign CPA increases by over 15%.",
                category=TriggerCategory.MARKETING,
                condition=TriggerCondition(
                    metric_key="meta_cpa_pct_change",
                    operator=">",
                    threshold=15.0,
                ),
                severity=TriggerSeverity.WARNING,
                enabled=True,
            ),
            EventTrigger(
                id="trg_fulfillment_exceptions",
                name="Fulfillment Exception Spike",
                description="Triggered when open order exceptions exceed threshold.",
                category=TriggerCategory.OPERATIONS,
                condition=TriggerCondition(
                    metric_key="fulfillment_open_exceptions",
                    operator=">",
                    threshold=10.0,
                ),
                severity=TriggerSeverity.CRITICAL,
                enabled=True,
            ),
            EventTrigger(
                id="trg_pipeline_stagnation",
                name="Sales Pipeline Stagnation",
                description="Triggered when deals linger in proposal stage > 14 days.",
                category=TriggerCategory.SALES,
                condition=TriggerCondition(
                    metric_key="stagnant_deals_count",
                    operator=">",
                    threshold=2.0,
                ),
                severity=TriggerSeverity.INFO,
                enabled=True,
            ),
        ]
        for trg in builtins:
            self._triggers[trg.id] = trg

    def _seed_builtin_goals(self) -> None:
        """Seed default strategic business goal trees."""
        goals = [
            GoalTree(
                id="goal_revenue_expansion_q4",
                title="Achieve ₹1,000,000 Monthly Revenue",
                description="Expand multi-channel sales and Meta acquisition to hit ₹10L/mo.",
                category=TriggerCategory.SALES,
                target_date="2026-12-31",
                status=GoalStatus.IN_PROGRESS,
                progress_percentage=48.5,
                milestones=[
                    GoalMilestone(
                        title="Reach ₹600k Monthly Revenue",
                        target_value=600000.0,
                        current_value=485000.0,
                        unit="INR",
                        target_date="2026-09-30",
                        completed=False,
                    ),
                    GoalMilestone(
                        title="Reach ₹1,000k Monthly Revenue",
                        target_value=1000000.0,
                        current_value=485000.0,
                        unit="INR",
                        target_date="2026-12-31",
                        completed=False,
                    ),
                ],
            ),
            GoalTree(
                id="goal_meta_roas_scale",
                title="Scale Meta ROAS to > 3.5x",
                description=(
                    "Optimize creative fatigue and ad spend to maintain profitable acquisition."
                ),
                category=TriggerCategory.MARKETING,
                target_date="2026-10-31",
                status=GoalStatus.IN_PROGRESS,
                progress_percentage=78.8,
                milestones=[
                    GoalMilestone(
                        title="Achieve ROAS 3.0x",
                        target_value=3.0,
                        current_value=2.76,
                        unit="x",
                        target_date="2026-09-15",
                        completed=False,
                    ),
                    GoalMilestone(
                        title="Achieve ROAS 3.5x",
                        target_value=3.5,
                        current_value=2.76,
                        unit="x",
                        target_date="2026-10-31",
                        completed=False,
                    ),
                ],
            ),
            GoalTree(
                id="goal_recover_receivables",
                title="Recover 100% Overdue Receivables",
                description="Automate payment follow-ups to collect all overdue client balances.",
                category=TriggerCategory.FINANCE,
                target_date="2026-09-15",
                status=GoalStatus.IN_PROGRESS,
                progress_percentage=35.0,
                milestones=[
                    GoalMilestone(
                        title="Recover ₹50,000 overdue",
                        target_value=50000.0,
                        current_value=29750.0,
                        unit="INR",
                        target_date="2026-08-31",
                        completed=False,
                    ),
                    GoalMilestone(
                        title="Recover total ₹85,000 overdue",
                        target_value=85000.0,
                        current_value=29750.0,
                        unit="INR",
                        target_date="2026-09-15",
                        completed=False,
                    ),
                ],
            ),
        ]
        for g in goals:
            self._goals[g.id] = g

    def create_trigger(
        self,
        name: str,
        description: str,
        category: str,
        metric_key: str,
        operator: str,
        threshold: float,
        severity: str = TriggerSeverity.WARNING,
        enabled: bool = True,
    ) -> EventTrigger:
        """Create and register a custom proactive business event trigger."""
        trigger_id = f"trg_{uuid4().hex[:8]}"
        trigger = EventTrigger(
            id=trigger_id,
            name=name,
            description=description,
            category=category,
            condition=TriggerCondition(
                metric_key=metric_key,
                operator=operator,
                threshold=threshold,
            ),
            severity=severity,
            enabled=enabled,
        )
        self._triggers[trigger_id] = trigger
        return trigger

    def list_triggers(self, category: str | None = None) -> list[EventTrigger]:
        """List registered event triggers, optionally filtered by category."""
        triggers = list(self._triggers.values())
        if category:
            triggers = [t for t in triggers if t.category == category]
        return triggers

    def get_trigger(self, trigger_id: str) -> EventTrigger | None:
        """Retrieve a trigger by identifier."""
        return self._triggers.get(trigger_id)

    def create_goal(
        self,
        title: str,
        description: str,
        category: str,
        target_date: str,
        milestones: list[dict[str, Any]] | None = None,
    ) -> GoalTree:
        """Create and track a strategic goal tree."""
        goal_id = f"goal_{uuid4().hex[:8]}"
        ms_objs: list[GoalMilestone] = []
        if milestones:
            for ms in milestones:
                ms_objs.append(
                    GoalMilestone(
                        title=str(ms.get("title", "")),
                        target_value=float(ms.get("target_value", 0.0)),
                        current_value=float(ms.get("current_value", 0.0)),
                        unit=str(ms.get("unit", "")),
                        target_date=str(ms.get("target_date", target_date)),
                        completed=bool(ms.get("completed", False)),
                    )
                )

        goal = GoalTree(
            id=goal_id,
            title=title,
            description=description,
            category=category,
            target_date=target_date,
            status=GoalStatus.IN_PROGRESS,
            progress_percentage=0.0,
            milestones=ms_objs,
        )
        self._goals[goal_id] = goal
        return goal

    def list_goals(self, category: str | None = None) -> list[GoalTree]:
        """List active strategic goals and progress."""
        goals = list(self._goals.values())
        if category:
            goals = [g for g in goals if g.category == category]
        return goals

    def get_goal(self, goal_id: str) -> GoalTree | None:
        """Retrieve a goal tree by identifier."""
        return self._goals.get(goal_id)

    def _evaluate_condition(self, condition: TriggerCondition, metric_val: float) -> bool:
        """Deterministically evaluate numerical condition."""
        op = condition.operator
        thresh = condition.threshold
        if op == "<":
            return metric_val < thresh
        if op == "<=":
            return metric_val <= thresh
        if op == ">":
            return metric_val > thresh
        if op == ">=":
            return metric_val >= thresh
        if op == "==":
            return metric_val == thresh
        if op == "!=":
            return metric_val != thresh
        if op == "pct_change_gt":
            return metric_val > thresh
        return False

    def evaluate_business_state(
        self,
        metrics_override: dict[str, float] | None = None,
    ) -> ProactiveEvaluationReport:
        """Evaluate all active business triggers against live business metrics.

        Produces actionable observations and autonomous intervention recommendations:
        'You don't need to do anything right now, but I found X.'
        """
        now_iso = datetime.now(UTC).isoformat()

        # Telemetry state baseline
        metrics: dict[str, float] = {
            "cash_runway_months": 5.4,
            "overdue_invoices_count": 2.0,
            "overdue_amount_inr": 85000.0,
            "meta_cpa_pct_change": 18.5,
            "fulfillment_open_exceptions": 3.0,
            "stagnant_deals_count": 4.0,
            "system_errors_count": 0.0,
        }
        if metrics_override:
            metrics.update(metrics_override)

        fired_triggers: list[EventTrigger] = []
        new_insights: list[ProactiveInsight] = []
        critical_alerts: list[str] = []

        for trg in self._triggers.values():
            if not trg.enabled:
                continue

            trg.last_checked_at = now_iso
            metric_val = metrics.get(trg.condition.metric_key)
            if metric_val is None:
                continue

            fired = self._evaluate_condition(trg.condition, metric_val)
            if fired:
                trg.last_fired_at = now_iso
                trg.firing_count += 1
                fired_triggers.append(trg)

                # Formulate specialized proactive advice
                insight = self._synthesize_insight(trg, metric_val, metrics)
                new_insights.append(insight)
                if trg.severity == TriggerSeverity.CRITICAL:
                    critical_alerts.append(
                        f"CRITICAL: {trg.name} ({metric_val} vs {trg.condition.threshold})"
                    )

        self._insights = new_insights

        report = ProactiveEvaluationReport(
            timestamp=now_iso,
            triggers_evaluated_count=len(self._triggers),
            triggers_fired_count=len(fired_triggers),
            active_insights_count=len(new_insights),
            goals_tracked_count=len(self._goals),
            critical_alerts=critical_alerts,
            insights=new_insights,
        )
        return report

    def _synthesize_insight(
        self,
        trigger: EventTrigger,
        metric_val: float,
        all_metrics: dict[str, float],
    ) -> ProactiveInsight:
        """Synthesize structured proactive insight with recommended capability action."""
        insight_id = f"ins_{uuid4().hex[:8]}"

        if trigger.id == "trg_overdue_invoices":
            overdue_amt = all_metrics.get("overdue_amount_inr", 85000.0)
            return ProactiveInsight(
                id=insight_id,
                trigger_id=trigger.id,
                severity=trigger.severity,
                title="Overdue Client Invoices Identified",
                observation=(
                    f"You don't need to do anything right now, but I identified {int(metric_val)} "
                    f"overdue invoices totaling ₹{overdue_amt:,.2f}."
                ),
                impact_summary=(
                    "Delayed receivables reduce operating runway and increase cashflow uncertainty."
                ),
                recommended_action=(
                    "Execute automated payment reminders via WhatsApp/Email to recover ₹85,000."
                ),
                auto_action_capability="comms.followup.schedule",
                auto_action_arguments={
                    "recipient": "clients",
                    "channel": "whatsapp",
                    "template": "invoice_reminder",
                },
            )

        if trigger.id == "trg_meta_cpa_fatigue":
            return ProactiveInsight(
                id=insight_id,
                trigger_id=trigger.id,
                severity=trigger.severity,
                title="Meta Ad CPA Fatigue Detected",
                observation=(
                    f"You don't need to do anything right now, but Meta ad CPA has increased "
                    f"by {metric_val:.1f}% over the last 7 days."
                ),
                impact_summary="Blended CPA is trending upwards, eroding margin efficiency.",
                recommended_action=(
                    "Pause fatigued ad creative 'Creative_B_Video' and "
                    "reallocate budget to top performers."
                ),
                auto_action_capability="marketing.intelligence.creative_fatigue",
                auto_action_arguments={"account_id": "act_default"},
            )

        if trigger.id == "trg_pipeline_stagnation":
            return ProactiveInsight(
                id=insight_id,
                trigger_id=trigger.id,
                severity=trigger.severity,
                title="Sales Pipeline Stagnation in Proposal Stage",
                observation=(
                    f"You don't need to do anything right now, but {int(metric_val)} high-value "
                    f"deals have been in proposal stage without buyer activity for >14 days."
                ),
                impact_summary="Stagnant proposals decrease quarter close rates from 32% to <15%.",
                recommended_action=(
                    "Trigger automated executive check-in email sequence to decision makers."
                ),
                auto_action_capability="comms.email.send",
                auto_action_arguments={"subject": "Project Proposal Follow-Up"},
            )

        if trigger.id == "trg_low_runway":
            return ProactiveInsight(
                id=insight_id,
                trigger_id=trigger.id,
                severity=trigger.severity,
                title="Critical Cash Runway Warning",
                observation=(
                    f"You don't need to do anything right now, but calculated cash runway "
                    f"has dropped to {metric_val:.1f} months."
                ),
                impact_summary="Operating cash is below the 3.0-month safety threshold.",
                recommended_action=(
                    "Initiate cost containment and accelerate accounts receivable collections."
                ),
                auto_action_capability="business.finance.overview",
                auto_action_arguments={},
            )

        # Generic fallback
        return ProactiveInsight(
            id=insight_id,
            trigger_id=trigger.id,
            severity=trigger.severity,
            title=f"Proactive Alert: {trigger.name}",
            observation=(
                f"You don't need to do anything right now, but "
                f"{trigger.condition.metric_key} reached {metric_val}."
            ),
            impact_summary="Business metric deviated from declared policy thresholds.",
            recommended_action=f"Inspect telemetry and adjust targets for {trigger.name}.",
        )

    def get_active_insights(self) -> list[ProactiveInsight]:
        """Return cached list of active proactive insights."""
        return list(self._insights)
