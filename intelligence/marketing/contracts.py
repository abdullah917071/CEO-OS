"""Data contracts and schemas for Marketing Intelligence and Multi-Channel Attribution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdSpendMetric:
    """Advertising channel spend and engagement metrics."""

    channel: str  # meta | google | youtube | total
    spend: float
    impressions: int
    clicks: int
    cpc: float
    cpm: float
    ctr: float


@dataclass
class TrafficMetric:
    """Website traffic and engagement metrics from Google Analytics."""

    sessions: int
    unique_visitors: int
    pageviews: int
    bounce_rate: float
    avg_session_duration_s: float


@dataclass
class CrmMetric:
    """CRM lead pipeline metrics."""

    leads_generated: int
    mql_count: int
    sql_count: int
    pipeline_value: float
    cac: float


@dataclass
class SalesMetric:
    """E-commerce and financial revenue metrics."""

    gross_revenue: float
    net_revenue: float
    cogs: float
    gross_profit: float
    net_profit: float
    orders_count: int
    aov: float
    refunds_amount: float
    refund_rate: float


@dataclass
class CreativePerformance:
    """Creative asset efficiency and fatigue status."""

    creative_id: str
    name: str
    channel: str
    spend: float
    conversions: int
    cpa: float
    roas: float
    fatigue_score: float  # 0.0 (fresh) to 1.0 (heavily fatigued)
    status: str  # "winning" | "testing" | "fatigued" | "underperforming"


@dataclass
class MarketingSnapshot:
    """Unified cross-channel marketing and business snapshot for a specific day."""

    date: str
    spend_by_channel: list[AdSpendMetric]
    total_spend: float
    traffic: TrafficMetric
    crm: CrmMetric
    sales: SalesMetric
    creatives: list[CreativePerformance] = field(default_factory=list)


@dataclass
class AttributionPeriodComparison:
    """Comparative multi-channel performance comparison between two dates."""

    period_a: str
    period_b: str
    revenue_change: float
    profit_change: float
    spend_change: float
    cpa_change: float
    conversion_rate_change: float
    primary_drivers: list[str] = field(default_factory=list)
    diagnosis: str = ""


@dataclass
class ProfitDiagnosticReport:
    """Root-cause diagnostic answering 'Why did profit fall yesterday?'."""

    date: str
    compare_date: str
    gross_revenue: float
    total_ad_spend: float
    net_profit: float
    profit_delta_percentage: float
    root_causes: list[str] = field(default_factory=list)
    channel_breakdown: dict[str, Any] = field(default_factory=dict)
    creative_fatigue_alerts: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    summary: str = ""
