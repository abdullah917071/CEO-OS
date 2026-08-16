"""Capability tools for Finance, Sales, Operations, and CEO Executive Briefings."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from intelligence.business.engine import BusinessExecutiveEngine


class BusinessExecutiveOverviewTool:
    """Tool to synthesize a full multi-department executive status report."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.executive.overview",
            description="Synthesize an executive status report answering 'CEO, what's happening?'",
            input_schema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "ISO date for overview",
                        "default": "2026-08-16",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        date = str(arguments.get("date", "2026-08-16"))
        overview = self._engine.get_executive_overview(date=date)
        return ToolResult(
            output=dataclasses.asdict(overview),
            evidence=[
                f"Executive Status: {overview.headline_status}; "
                f"Revenue Growth: +{overview.revenue_growth_pct}%; "
                f"Summary: {overview.summary}"
            ],
        )


class BusinessFinanceOverviewTool:
    """Tool to inspect consolidated financial health and cash position."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.finance.overview",
            description="Get consolidated financial metrics, cash balance, profit, and receivables",
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        fin = self._engine.get_financial_overview()
        return ToolResult(
            output=dataclasses.asdict(fin),
            evidence=[
                f"Financial Overview: Cash {fin.currency} {fin.cash_balance:,.0f}; "
                f"Revenue MTD {fin.currency} {fin.total_revenue_mtd:,.0f}; "
                f"Net Profit MTD {fin.currency} {fin.net_profit_mtd:,.0f}; "
                f"Overdue Receivables {fin.currency} {fin.receivables_overdue:,.0f}"
            ],
        )


class BusinessFinanceAffordabilityTool:
    """Tool to run capital allocation simulations and runway forecasting."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.finance.affordability",
            description="Simulate financial affordability and runway impact (e.g. ad push spend)",
            input_schema={
                "type": "object",
                "properties": {
                    "proposed_spend": {
                        "type": "number",
                        "description": "Proposed expenditure amount",
                        "default": 200000.0,
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Purpose of expenditure",
                        "default": "advertising push",
                    },
                    "currency": {"type": "string", "default": "INR"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        proposed_spend = float(arguments.get("proposed_spend", 200000.0))
        purpose = str(arguments.get("purpose", "advertising push"))
        currency = str(arguments.get("currency", "INR"))

        sim = self._engine.simulate_affordability(
            proposed_spend=proposed_spend, purpose=purpose, currency=currency
        )
        return ToolResult(
            output=dataclasses.asdict(sim),
            evidence=[
                f"Affordability Verdict: {sim.affordability_verdict}; "
                f"Cash Cushion Remaining: {sim.currency} {sim.cash_buffer_remaining:,.0f}; "
                f"Runway Impact: -{sim.projected_runway_impact_months} months; "
                f"Recommendation: {sim.recommendation}"
            ],
        )


class BusinessFinanceInvoicesTool:
    """Tool to inspect billing and accounts receivable invoices."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.finance.invoices",
            description="List billing invoices and track unpaid or overdue client balances",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["PAID", "OVERDUE", "PENDING"],
                        "description": "Optional status filter",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        status = arguments.get("status")
        invoices = self._engine.list_invoices(status=status)
        return ToolResult(
            output=[dataclasses.asdict(i) for i in invoices],
            evidence=[f"Found {len(invoices)} invoice(s) matching status '{status or 'ALL'}'"],
        )


class BusinessSalesPipelineTool:
    """Tool to inspect sales pipeline velocity, stages, and weighted forecast."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.sales.pipeline",
            description="Get sales pipeline summary with stages, weighted forecast, and win rates",
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        pipe = self._engine.get_sales_pipeline()
        return ToolResult(
            output=dataclasses.asdict(pipe),
            evidence=[
                f"Sales Pipeline: {pipe.total_deals} active deal(s); "
                f"Pipeline Value ₹{pipe.pipeline_value:,.0f} "
                f"(Weighted ₹{pipe.weighted_value:,.0f}); "
                f"Closed Won this month ₹{pipe.won_this_month:,.0f}"
            ],
        )


class BusinessSalesDealsTool:
    """Tool to list sales opportunities across stages."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.sales.deals",
            description="List sales opportunities filtered by lifecycle stage",
            input_schema={
                "type": "object",
                "properties": {
                    "stage": {
                        "type": "string",
                        "enum": [
                            "lead",
                            "qualified",
                            "meeting_scheduled",
                            "proposal_sent",
                            "closed_won",
                            "closed_lost",
                        ],
                        "description": "Optional stage filter",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        stage = arguments.get("stage")
        deals = self._engine.list_deals(stage=stage)
        return ToolResult(
            output=[dataclasses.asdict(d) for d in deals],
            evidence=[f"Found {len(deals)} sales opportunity deal(s)"],
        )


class BusinessOperationsHealthTool:
    """Tool to inspect fulfillment rates, order exceptions, and supplier status."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.operations.health",
            description="Get operational health, order fulfillment rate, and exceptions",
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        health = self._engine.get_operations_health()
        return ToolResult(
            output=dataclasses.asdict(health),
            evidence=[
                f"Operations Health: Fulfillment Rate {health.fulfillment_rate}%; "
                f"Orders Today {health.total_orders_today}; "
                f"Open Exceptions {len(health.open_exceptions)}; "
                f"Refund Rate {health.refund_rate_percentage}%"
            ],
        )


class BusinessOperationsInventoryTool:
    """Tool to inspect inventory stock levels and reorder triggers."""

    def __init__(self, engine: BusinessExecutiveEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="business.operations.inventory",
            description="Inspect inventory stock levels and reorder trigger alerts",
            input_schema={
                "type": "object",
                "properties": {
                    "low_stock_only": {
                        "type": "boolean",
                        "description": "Filter to only low stock items",
                        "default": False,
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:business",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        low_stock = bool(arguments.get("low_stock_only", False))
        items = self._engine.list_inventory(low_stock_only=low_stock)
        return ToolResult(
            output=[dataclasses.asdict(i) for i in items],
            evidence=[f"Found {len(items)} inventory SKU item(s)"],
        )
