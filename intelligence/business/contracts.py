"""Data contracts and models for Finance, Sales, Operations, and Executive Overview."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DealStage(StrEnum):
    """Lifecycle stages for enterprise and B2B sales pipeline deals."""

    LEAD = "lead"
    QUALIFIED = "qualified"
    MEETING_SCHEDULED = "meeting_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


@dataclass
class Invoice:
    """Accounts receivable and billing invoice contract."""

    invoice_id: str
    client_name: str
    amount: float
    currency: str
    status: str  # "PAID" | "OVERDUE" | "PENDING"
    due_date: str
    issued_date: str
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Subscription:
    """Recurring vendor and SaaS subscription with price tracking."""

    subscription_id: str
    vendor: str
    category: str
    monthly_amount: float
    currency: str
    previous_amount: float
    delta_amount: float
    status: str  # "ACTIVE" | "INCREASED" | "CANCELLED"


@dataclass
class FinancialRunway:
    """Cash position, burn rate, and runway calculation."""

    cash_balance: float
    monthly_burn_rate: float
    monthly_revenue: float
    runway_months: float
    currency: str


@dataclass
class AffordabilitySimulation:
    """Financial forecasting and capital allocation simulation."""

    scenario: str
    proposed_spend: float
    currency: str
    affordability_verdict: str  # "AFFORDABLE" | "HIGH_RISK" | "UNRECOMMENDED"
    projected_runway_impact_months: float
    breakeven_units_or_conversions: int
    cash_buffer_remaining: float
    recommendation: str


@dataclass
class FinancialOverview:
    """Consolidated financial health snapshot."""

    cash_balance: float
    total_revenue_mtd: float
    total_expenses_mtd: float
    net_profit_mtd: float
    receivables_total: float
    receivables_overdue: float
    unpaid_invoices: list[Invoice]
    subscriptions: list[Subscription]
    currency: str


@dataclass
class Deal:
    """Sales pipeline opportunity record."""

    deal_id: str
    deal_name: str
    prospect_name: str
    stage: DealStage
    value: float
    currency: str
    win_probability: float
    expected_close_date: str
    owner: str
    last_activity: str


@dataclass
class SalesPipelineSummary:
    """Consolidated sales pipeline telemetry."""

    total_deals: int
    pipeline_value: float
    weighted_value: float
    stage_breakdown: dict[str, int]
    top_deals: list[Deal]
    won_this_month: float
    win_rate: float


@dataclass
class InventoryItem:
    """Operations physical goods or inventory record."""

    sku: str
    name: str
    category: str
    stock_level: int
    reorder_point: int
    unit_cost: float
    status: str  # "IN_STOCK" | "LOW_STOCK" | "OUT_OF_STOCK"


@dataclass
class OrderException:
    """Operational anomaly or order fulfillment exception."""

    order_id: str
    customer_name: str
    issue_type: str  # "DELAYED_SHIPMENT" | "REFUND_REQUESTED" | "PAYMENT_HOLD"
    status: str  # "OPEN" | "RESOLVED"
    created_at: str
    urgency: str  # "LOW" | "NORMAL" | "HIGH" | "URGENT"


@dataclass
class OperationsHealth:
    """Fulfillment, inventory, refund rates, and supply chain telemetry."""

    total_orders_today: int
    fulfillment_rate: float
    open_exceptions: list[OrderException]
    low_stock_items: list[InventoryItem]
    refund_rate_percentage: float
    supplier_status: str


@dataclass
class ExecutiveBusinessOverview:
    """Multi-department executive briefing synthesized for the CEO."""

    date: str
    headline_status: str  # "HEALTHY" | "NEEDS_ATTENTION" | "CRITICAL"
    revenue_growth_pct: float
    marketing_summary: str
    finance_summary: str
    sales_summary: str
    operations_summary: str
    unpaid_invoices: list[Invoice]
    subscription_alerts: list[Subscription]
    action_items: list[str]
    summary: str
