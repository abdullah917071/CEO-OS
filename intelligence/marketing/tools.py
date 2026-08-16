"""Capability tools for Marketing Intelligence, Attribution, and Profit Diagnostics."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from intelligence.marketing.engine import MarketingIntelligenceEngine


class MarketingProfitDiagnoseTool:
    """Tool to diagnose root causes of company profit fluctuations."""

    def __init__(self, engine: MarketingIntelligenceEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="marketing.profit.diagnose",
            description=(
                "Diagnose why profit changed yesterday or between dates by correlating "
                "Meta/Google ad spend, website traffic, CRM pipeline, and sales revenue"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date to diagnose (e.g. 2026-08-15 or yesterday)",
                        "default": "2026-08-15",
                    },
                    "compare_date": {
                        "type": "string",
                        "description": "Baseline date for comparison (e.g. 2026-08-14)",
                        "default": "2026-08-14",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:marketing",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        date_val = str(arguments.get("date", "2026-08-15"))
        compare_date = str(arguments.get("compare_date", "2026-08-14"))
        report = self._engine.diagnose_profit_change(
            current_date=date_val, previous_date=compare_date
        )

        evidence = [
            f"Profit Diagnosis: {report.summary}",
            f"Primary Root Causes: {'; '.join(report.root_causes)}",
            f"Recommended Actions: {'; '.join(report.recommended_actions[:2])}",
        ]
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=evidence,
        )


class MarketingAttributionFunnelTool:
    """Tool to retrieve full-funnel marketing attribution metrics."""

    def __init__(self, engine: MarketingIntelligenceEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="marketing.attribution.funnel",
            description=(
                "Get end-to-end multi-channel attribution funnel: "
                "Ad Spend -> Clicks -> Site Sessions -> Leads -> Orders -> Revenue -> Profit"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "date_start": {"type": "string", "default": "2026-08-01"},
                    "date_stop": {"type": "string", "default": "2026-08-15"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:marketing",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        d_start = str(arguments.get("date_start", "2026-08-01"))
        d_stop = str(arguments.get("date_stop", "2026-08-15"))
        funnel = self._engine.get_attribution_funnel(date_start=d_start, date_stop=d_stop)
        return ToolResult(
            output=funnel,
            evidence=[
                f"Attribution Funnel: Blended ROAS={funnel['roas']}x, CAC=₹{funnel['cac']}, "
                f"Contribution Margin={funnel['contribution_margin_pct']}%"
            ],
        )


class MarketingCreativesAnalyzeTool:
    """Tool to analyze creative asset decay and fatigue scores."""

    def __init__(self, engine: MarketingIntelligenceEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="marketing.creatives.analyze",
            description=(
                "Analyze creative performance, asset decay, and fatigue scores across channels"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "timeframe": {"type": "string", "default": "7d"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:marketing",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        tf = str(arguments.get("timeframe", "7d"))
        creatives = self._engine.analyze_creatives(timeframe=tf)
        details = ", ".join(
            f"'{c.name}' status={c.status} (fatigue={c.fatigue_score})" for c in creatives
        )
        return ToolResult(
            output=[dataclasses.asdict(c) for c in creatives],
            evidence=[f"Analyzed {len(creatives)} creative asset(s): {details}"],
        )


class MarketingSnapshotGetTool:
    """Tool to retrieve daily holistic business & marketing snapshot."""

    def __init__(self, engine: MarketingIntelligenceEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="marketing.snapshot.get",
            description="Retrieve unified daily marketing, traffic, CRM, and sales snapshot",
            input_schema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "default": "2026-08-15"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:marketing",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        date_str = str(arguments.get("date", "2026-08-15"))
        snap = self._engine.get_daily_snapshot(date_str)
        return ToolResult(
            output=dataclasses.asdict(snap),
            evidence=[
                f"Marketing Snapshot for {snap.date}: Total Ad Spend=₹{snap.total_spend:,.2f}, "
                f"Sessions={snap.traffic.sessions}, Revenue=₹{snap.sales.net_revenue:,.2f}, "
                f"Net Profit=₹{snap.sales.net_profit:,.2f}"
            ],
        )
