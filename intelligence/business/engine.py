"""Business Executive Engine: Finance, Sales, Operations, and CEO Briefing."""

from __future__ import annotations

import logging

from intelligence.business.contracts import (
    AffordabilitySimulation,
    Deal,
    DealStage,
    ExecutiveBusinessOverview,
    FinancialOverview,
    FinancialRunway,
    InventoryItem,
    Invoice,
    OperationsHealth,
    OrderException,
    SalesPipelineSummary,
    Subscription,
)

logger = logging.getLogger(__name__)


class BusinessExecutiveEngine:
    """Consolidated business operating system uniting Finance, Sales, Operations,

    and multi-department executive briefings for the CEO.
    """

    def __init__(self) -> None:
        self._invoices: dict[str, Invoice] = {
            "inv_8901": Invoice(
                invoice_id="inv_8901",
                client_name="Apex Enterprise",
                amount=150000.0,
                currency="INR",
                status="OVERDUE",
                due_date="2026-08-15",
                issued_date="2026-08-01",
                items=[{"description": "Enterprise Platform Retainer", "qty": 1, "rate": 150000.0}],
            ),
            "inv_8902": Invoice(
                invoice_id="inv_8902",
                client_name="Starlight Digital",
                amount=85000.0,
                currency="INR",
                status="OVERDUE",
                due_date="2026-08-15",
                issued_date="2026-08-01",
                items=[
                    {"description": "Performance Optimization Sprint", "qty": 1, "rate": 85000.0}
                ],
            ),
            "inv_8903": Invoice(
                invoice_id="inv_8903",
                client_name="Nordic SaaS",
                amount=265000.0,
                currency="INR",
                status="PENDING",
                due_date="2026-08-21",
                issued_date="2026-08-07",
                items=[{"description": "AI Agent Integration License", "qty": 1, "rate": 265000.0}],
            ),
            "inv_8900": Invoice(
                invoice_id="inv_8900",
                client_name="Horizon Media",
                amount=320000.0,
                currency="INR",
                status="PAID",
                due_date="2026-08-10",
                issued_date="2026-07-25",
                items=[{"description": "Monthly Workflow Automation", "qty": 1, "rate": 320000.0}],
            ),
        }

        self._subscriptions: dict[str, Subscription] = {
            "sub_host_01": Subscription(
                subscription_id="sub_host_01",
                vendor="Cloud VPS Cluster",
                category="Infrastructure",
                monthly_amount=14200.0,
                currency="INR",
                previous_amount=13000.0,
                delta_amount=1200.0,
                status="INCREASED",
            ),
            "sub_crm_02": Subscription(
                subscription_id="sub_crm_02",
                vendor="HubSpot CRM Suite",
                category="Sales & Marketing",
                monthly_amount=18500.0,
                currency="INR",
                previous_amount=18500.0,
                delta_amount=0.0,
                status="ACTIVE",
            ),
            "sub_ai_03": Subscription(
                subscription_id="sub_ai_03",
                vendor="OpenAI Gateway & Vectors",
                category="AI Infrastructure",
                monthly_amount=22000.0,
                currency="INR",
                previous_amount=22000.0,
                delta_amount=0.0,
                status="ACTIVE",
            ),
        }

        self._deals: dict[str, Deal] = {
            "deal_01": Deal(
                deal_id="deal_01",
                deal_name="Enterprise CEO OS Deployment",
                prospect_name="Apex Logistics",
                stage=DealStage.PROPOSAL_SENT,
                value=450000.0,
                currency="INR",
                win_probability=0.70,
                expected_close_date="2026-08-25",
                owner="Sales Director",
                last_activity="Sent formal customized proposal with ROI matrix",
            ),
            "deal_02": Deal(
                deal_id="deal_02",
                deal_name="E-Commerce Automation Suite",
                prospect_name="Zenith Retail",
                stage=DealStage.MEETING_SCHEDULED,
                value=280000.0,
                currency="INR",
                win_probability=0.50,
                expected_close_date="2026-08-28",
                owner="Sales Director",
                last_activity="Demo scheduled for Friday 3 PM",
            ),
            "deal_03": Deal(
                deal_id="deal_03",
                deal_name="AI Telephony Operations",
                prospect_name="Nexus Health",
                stage=DealStage.QUALIFIED,
                value=600000.0,
                currency="INR",
                win_probability=0.35,
                expected_close_date="2026-09-10",
                owner="Account Executive",
                last_activity="Completed discovery call with VP of Operations",
            ),
            "deal_04": Deal(
                deal_id="deal_04",
                deal_name="Global Logistics Sync",
                prospect_name="Vanguard Freight",
                stage=DealStage.CLOSED_WON,
                value=520000.0,
                currency="INR",
                win_probability=1.0,
                expected_close_date="2026-08-12",
                owner="Account Executive",
                last_activity="Contract signed and onboarding initiated",
            ),
        }

        self._inventory: dict[str, InventoryItem] = {
            "sku_box_01": InventoryItem(
                sku="sku_box_01",
                name="Thermal Packing Enclosures",
                category="Packaging",
                stock_level=14,
                reorder_point=50,
                unit_cost=120.0,
                status="LOW_STOCK",
            ),
            "sku_lbl_02": InventoryItem(
                sku="sku_lbl_02",
                name="Barcode Shipping Labels (1000ct)",
                category="Fulfillment Supplies",
                stock_level=85,
                reorder_point=30,
                unit_cost=450.0,
                status="IN_STOCK",
            ),
            "sku_tape_03": InventoryItem(
                sku="sku_tape_03",
                name="Reinforced Adhesive Kraft Tape",
                category="Packaging",
                stock_level=110,
                reorder_point=40,
                unit_cost=180.0,
                status="IN_STOCK",
            ),
        }

        self._exceptions: dict[str, OrderException] = {
            "exc_01": OrderException(
                order_id="ORD-84912",
                customer_name="Rohan Verma",
                issue_type="DELAYED_SHIPMENT",
                status="OPEN",
                created_at="2026-08-15T18:30:00Z",
                urgency="HIGH",
            ),
            "exc_02": OrderException(
                order_id="ORD-84877",
                customer_name="Priya Sharma",
                issue_type="REFUND_REQUESTED",
                status="OPEN",
                created_at="2026-08-16T08:15:00Z",
                urgency="NORMAL",
            ),
        }

    # ── Finance Engine ──────────────────────────────────────────────────────────

    def get_financial_overview(self) -> FinancialOverview:
        """Get consolidated financial health metrics, cash balance, and receivables."""
        invoices = list(self._invoices.values())
        unpaid = [i for i in invoices if i.status in {"OVERDUE", "PENDING"}]
        overdue = [i for i in invoices if i.status == "OVERDUE"]

        total_rec = sum(i.amount for i in unpaid)
        total_overdue = sum(i.amount for i in overdue)

        return FinancialOverview(
            cash_balance=1840000.0,
            total_revenue_mtd=1280000.0,
            total_expenses_mtd=740000.0,
            net_profit_mtd=540000.0,
            receivables_total=total_rec,
            receivables_overdue=total_overdue,
            unpaid_invoices=unpaid,
            subscriptions=list(self._subscriptions.values()),
            currency="INR",
        )

    def get_financial_runway(self) -> FinancialRunway:
        """Calculate cash runway and monthly burn metrics."""
        cash = 1840000.0
        monthly_burn = 225000.0  # Net monthly burn (expenses - base recurring revenue)
        monthly_rev = 1280000.0
        runway = round(cash / monthly_burn, 1) if monthly_burn > 0 else 99.0

        return FinancialRunway(
            cash_balance=cash,
            monthly_burn_rate=monthly_burn,
            monthly_revenue=monthly_rev,
            runway_months=runway,
            currency="INR",
        )

    def simulate_affordability(
        self,
        proposed_spend: float = 200000.0,
        purpose: str = "advertising push",
        currency: str = "INR",
    ) -> AffordabilitySimulation:
        """Simulate financial affordability, capital allocation, and runway impact.

        Answers: 'Can we afford another ₹2 lakh advertising push?'
        """
        cash = 1840000.0
        remaining_cash = cash - proposed_spend
        monthly_burn = 225000.0
        new_runway = round(remaining_cash / monthly_burn, 1) if monthly_burn > 0 else 99.0
        current_runway = round(cash / monthly_burn, 1)
        impact = round(current_runway - new_runway, 1)

        # Assuming average order/contract gross margin contribution of ₹8,500
        breakeven_units = int((proposed_spend / 8500.0) + 0.99)

        if remaining_cash < 500000.0 or new_runway < 3.0:
            verdict = "HIGH_RISK"
            recommendation = (
                f"Unrecommended to spend {currency} {proposed_spend:,.0f}. "
                f"Remaining runway would drop to {new_runway} months below safety floor."
            )
        else:
            verdict = "AFFORDABLE"
            recommendation = (
                f"Approved. Cash cushion remains {currency} {remaining_cash:,.0f} "
                f"({new_runway} months runway). "
                f"Estimated breakeven requires {breakeven_units} units/conversions. "
                f"Target 3.2x ROAS to generate {currency} {proposed_spend * 3.2:,.0f}."
            )

        return AffordabilitySimulation(
            scenario=f"Capital Allocation for {purpose.title()}",
            proposed_spend=proposed_spend,
            currency=currency,
            affordability_verdict=verdict,
            projected_runway_impact_months=impact,
            breakeven_units_or_conversions=breakeven_units,
            cash_buffer_remaining=remaining_cash,
            recommendation=recommendation,
        )

    def list_invoices(self, status: str | None = None) -> list[Invoice]:
        """List accounts receivable invoices filtered by status."""
        results = list(self._invoices.values())
        if status:
            results = [i for i in results if i.status.upper() == status.upper()]
        return results

    def list_subscriptions(self, increased_only: bool = False) -> list[Subscription]:
        """List recurring software and infrastructure subscriptions."""
        results = list(self._subscriptions.values())
        if increased_only:
            results = [s for s in results if s.status == "INCREASED" or s.delta_amount > 0]
        return results

    # ── Sales Pipeline Engine ───────────────────────────────────────────────────

    def get_sales_pipeline(self) -> SalesPipelineSummary:
        """Get consolidated sales pipeline value, stage breakdown, and win rates."""
        deals = list(self._deals.values())
        total_val = sum(d.value for d in deals)
        weighted_val = sum(d.value * d.win_probability for d in deals)

        breakdown: dict[str, int] = {}
        for d in deals:
            breakdown[d.stage.value] = breakdown.get(d.stage.value, 0) + 1

        won_deals = [d for d in deals if d.stage == DealStage.CLOSED_WON]
        won_total = sum(d.value for d in won_deals)

        return SalesPipelineSummary(
            total_deals=len(deals),
            pipeline_value=total_val,
            weighted_value=round(weighted_val, 2),
            stage_breakdown=breakdown,
            top_deals=deals,
            won_this_month=won_total,
            win_rate=68.4,
        )

    def list_deals(self, stage: str | None = None) -> list[Deal]:
        """List sales opportunities filtered by lifecycle stage."""
        results = list(self._deals.values())
        if stage:
            results = [d for d in results if d.stage.value.lower() == stage.lower()]
        return results

    # ── Operations Engine ───────────────────────────────────────────────────────

    def get_operations_health(self) -> OperationsHealth:
        """Get operational fulfillment rate, open exceptions, and supply chain status."""
        inventory = list(self._inventory.values())
        low_stock = [i for i in inventory if i.status in {"LOW_STOCK", "OUT_OF_STOCK"}]
        exceptions = [e for e in self._exceptions.values() if e.status == "OPEN"]

        return OperationsHealth(
            total_orders_today=142,
            fulfillment_rate=98.6,
            open_exceptions=exceptions,
            low_stock_items=low_stock,
            refund_rate_percentage=1.4,
            supplier_status="All 3 primary suppliers active with 99.2% on-time delivery SLA",
        )

    def list_inventory(self, low_stock_only: bool = False) -> list[InventoryItem]:
        """List inventory items and reorder alerts."""
        results = list(self._inventory.values())
        if low_stock_only:
            results = [i for i in results if i.status in {"LOW_STOCK", "OUT_OF_STOCK"}]
        return results

    def list_order_exceptions(self) -> list[OrderException]:
        """List open operational order exceptions."""
        return [e for e in self._exceptions.values() if e.status == "OPEN"]

    # ── Executive Synthesis Briefing ────────────────────────────────────────────

    def get_executive_overview(self, date: str = "2026-08-16") -> ExecutiveBusinessOverview:
        """Synthesize a complete multi-department executive status report for the CEO.

        Answers: 'CEO, what's happening?'
        """
        invoices = self.list_invoices(status="OVERDUE")
        sub_alerts = self.list_subscriptions(increased_only=True)

        mkt_summary = (
            "Meta is performing well with strong ROAS (3.4x). "
            "Google CPA increased 19% (now ₹64.20), so Marketing is actively investigating."
        )
        fin_summary = (
            f"Two clients haven't paid invoices due yesterday ({invoices[0].client_name} ₹1.5L, "
            f"{invoices[1].client_name} ₹85k); Finance has prepared follow-ups. "
            f"Recurring hosting subscription increased by ₹1,200 this month (now ₹14,200/mo). "
            "Cash runway is strong at 8.2 months."
        )
        sales_summary = (
            "Pipeline active with ₹18.5L across 4 enterprise deals (₹11.85L weighted value), "
            "with ₹5.2L closed-won this month."
        )
        ops_summary = (
            "Fulfillment rate at 98.6% across 142 orders today. "
            "The developer finished the checkout update and QA is testing it. "
            "You have an executive call at 3:30 PM."
        )

        action_items = [
            "Marketing: Investigate Google CPA +19% spike and optimize search match types.",
            "Finance: Send follow-ups for overdue invoices inv_8901 (₹1.5L) and inv_8902 (₹85k).",
            "Operations: Review ₹1,200 hosting subscription increase with DevOps team.",
            "Calendar: Executive call at 3:30 PM (can reschedule to 5:00 PM if needed).",
        ]

        summary = (
            "Business is mostly healthy. Revenue yesterday was up 11%. "
            "Meta is performing well, but Google CPA increased 19%, "
            "so Marketing is investigating that. "
            "Two clients haven't paid invoices due yesterday; Finance has prepared follow-ups. "
            "The developer finished the checkout update and QA is testing it. "
            "You have a call at 3:30. "
            "I also found that your recurring hosting subscription increased by ₹1,200 this month."
        )

        return ExecutiveBusinessOverview(
            date=date,
            headline_status="HEALTHY",
            revenue_growth_pct=11.0,
            marketing_summary=mkt_summary,
            finance_summary=fin_summary,
            sales_summary=sales_summary,
            operations_summary=ops_summary,
            unpaid_invoices=invoices,
            subscription_alerts=sub_alerts,
            action_items=action_items,
            summary=summary,
        )
