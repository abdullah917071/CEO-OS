"""Data contracts and schemas for Meta Marketing API integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdAccount:
    """Meta Ad Account representation."""

    id: str
    name: str
    account_status: str = "ACTIVE"  # ACTIVE | PAUSED | DISABLED
    currency: str = "INR"
    timezone_name: str = "Asia/Kolkata"
    amount_spent: float = 0.0
    balance: float = 0.0


@dataclass
class Campaign:
    """Meta Advertising Campaign."""

    id: str
    account_id: str
    name: str
    objective: str  # OUTCOME_TRAFFIC | OUTCOME_SALES | OUTCOME_LEADS | OUTCOME_ENGAGEMENT
    status: str = "PAUSED"  # ACTIVE | PAUSED | ARCHIVED | DRAFT
    daily_budget: float | None = None
    lifetime_budget: float | None = None
    created_time: str = ""
    updated_time: str = ""


@dataclass
class AdSet:
    """Meta Ad Set specifying targeting, budget, and schedule."""

    id: str
    campaign_id: str
    name: str
    status: str = "PAUSED"
    daily_budget: float | None = None
    billing_event: str = "IMPRESSIONS"
    optimization_goal: str = "LINK_CLICKS"
    targeting: dict[str, Any] = field(default_factory=dict)
    bid_amount: float | None = None
    start_time: str = ""
    end_time: str | None = None


@dataclass
class AdCreative:
    """Meta Ad Creative containing copy, headline, and media assets."""

    id: str
    account_id: str
    name: str
    title: str
    body: str
    image_url: str | None = None
    link_url: str | None = None
    call_to_action_type: str = "LEARN_MORE"


@dataclass
class Ad:
    """Meta Ad linking a creative to an ad set."""

    id: str
    adset_id: str
    name: str
    creative_id: str
    status: str = "PAUSED"
    created_time: str = ""


@dataclass
class AdInsight:
    """Performance metrics for an advertising entity."""

    entity_id: str
    entity_type: str  # campaign | adset | ad | account
    date_start: str
    date_stop: str
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    cpc: float = 0.0
    cpm: float = 0.0
    ctr: float = 0.0
    conversions: int = 0
    roas: float = 0.0


@dataclass
class CampaignReport:
    """Comprehensive executive performance report for a campaign."""

    account_id: str
    campaign_id: str
    campaign_name: str
    status: str
    daily_budget: float
    currency: str
    total_spend: float
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    conversions: int
    roas: float
    summary: str
    insights: list[AdInsight] = field(default_factory=list)
