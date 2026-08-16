"""Meta Marketing API Client with official Graph API structures and deterministic simulation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from integrations.meta.contracts import (
    Ad,
    AdAccount,
    AdCreative,
    AdInsight,
    AdSet,
    Campaign,
    CampaignReport,
)
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)


class MetaClient:
    """Provider-neutral client for the Meta Marketing API."""

    def __init__(
        self,
        secret_broker: SecretBroker | None = None,
        credential_id: str = "meta_access_token",
    ) -> None:
        self._secret_broker = secret_broker
        self._credential_id = credential_id

        # In-memory deterministic advertising store
        self._accounts: dict[str, AdAccount] = {}
        self._campaigns: dict[str, Campaign] = {}
        self._adsets: dict[str, AdSet] = {}
        self._creatives: dict[str, AdCreative] = {}
        self._ads: dict[str, Ad] = {}
        self._insights: dict[str, list[AdInsight]] = {}
        self._seed_default_data()

    def _seed_default_data(self) -> None:
        """Seed initial ad account and sample campaigns."""
        acc_id = "act_1019283746"
        self._accounts[acc_id] = AdAccount(
            id=acc_id,
            name="CEO OS Growth Account",
            account_status="ACTIVE",
            currency="INR",
            timezone_name="Asia/Kolkata",
            amount_spent=24500.0,
            balance=15500.0,
        )

        camp_id = "cmp_847291048"
        self._campaigns[camp_id] = Campaign(
            id=camp_id,
            account_id=acc_id,
            name="Q3 Product Launch Promo",
            objective="OUTCOME_TRAFFIC",
            status="ACTIVE",
            daily_budget=800.0,
            created_time="2026-08-01T10:00:00Z",
            updated_time="2026-08-15T12:00:00Z",
        )

        adset_id = "adset_562819304"
        self._adsets[adset_id] = AdSet(
            id=adset_id,
            campaign_id=camp_id,
            name="Founders & Tech Leaders - India",
            status="ACTIVE",
            daily_budget=800.0,
            billing_event="IMPRESSIONS",
            optimization_goal="LINK_CLICKS",
            targeting={
                "geo_locations": {"countries": ["IN"]},
                "age_min": 25,
                "age_max": 55,
                "interests": [{"id": "6003139266783", "name": "Entrepreneurship"}],
            },
        )

        creative_id = "cr_738291045"
        self._creatives[creative_id] = AdCreative(
            id=creative_id,
            account_id=acc_id,
            name="Executive Automation Showcase",
            title="Automate Your Entire Company With CEO OS",
            body=(
                "From calendar to telephone calls to browser actions — your AI executive "
                "team works 24/7."
            ),
            image_url="https://images.unsplash.com/photo-1551836022-d5d88e9218df",
            link_url="https://ceo-os.internal/demo",
            call_to_action_type="LEARN_MORE",
        )

        ad_id = "ad_928174019"
        self._ads[ad_id] = Ad(
            id=ad_id,
            adset_id=adset_id,
            name="Showcase Ad 1",
            creative_id=creative_id,
            status="ACTIVE",
            created_time="2026-08-01T10:30:00Z",
        )

        # Seed sample insight
        self._insights[camp_id] = [
            AdInsight(
                entity_id=camp_id,
                entity_type="campaign",
                date_start="2026-08-01",
                date_stop="2026-08-15",
                impressions=42500,
                clicks=1380,
                spend=11200.0,
                cpc=8.12,
                cpm=263.53,
                ctr=3.25,
                conversions=84,
                roas=3.4,
            )
        ]

    # ── Accounts ─────────────────────────────────────────────────────────────

    async def list_ad_accounts(self) -> list[AdAccount]:
        """List all accessible Meta Ad Accounts."""
        return list(self._accounts.values())

    async def get_ad_account(self, account_id: str) -> AdAccount:
        """Get ad account details by ID."""
        acc = self._accounts.get(account_id)
        if not acc:
            raise ValueError(f"Ad account '{account_id}' not found")
        return acc

    # ── Campaigns ────────────────────────────────────────────────────────────

    async def list_campaigns(
        self,
        account_id: str | None = None,
        status_filter: str | None = None,
    ) -> list[Campaign]:
        """List campaigns with optional account and status filters."""
        camps = list(self._campaigns.values())
        if account_id:
            camps = [c for c in camps if c.account_id == account_id]
        if status_filter:
            camps = [c for c in camps if c.status.upper() == status_filter.upper()]
        return camps

    async def get_campaign(self, campaign_id: str) -> Campaign:
        """Get a single campaign by ID."""
        camp = self._campaigns.get(campaign_id)
        if not camp:
            raise ValueError(f"Campaign '{campaign_id}' not found")
        return camp

    async def create_campaign(
        self,
        account_id: str,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        status: str = "PAUSED",
        daily_budget: float | None = None,
        lifetime_budget: float | None = None,
    ) -> Campaign:
        """Create a new advertising campaign in Meta."""
        if account_id not in self._accounts:
            # Auto-register if new account ID referenced
            self._accounts[account_id] = AdAccount(id=account_id, name=f"Account {account_id}")

        camp_id = f"cmp_{uuid4().hex[:9]}"
        now = datetime.now(UTC).isoformat()
        camp = Campaign(
            id=camp_id,
            account_id=account_id,
            name=name,
            objective=objective,
            status=status.upper(),
            daily_budget=daily_budget,
            lifetime_budget=lifetime_budget,
            created_time=now,
            updated_time=now,
        )
        self._campaigns[camp_id] = camp
        logger.info("Created Meta campaign %s (%s)", camp.name, camp.id)
        return camp

    async def update_campaign(
        self,
        campaign_id: str,
        name: str | None = None,
        status: str | None = None,
        daily_budget: float | None = None,
    ) -> Campaign:
        """Update campaign name, status, or daily budget."""
        camp = await self.get_campaign(campaign_id)
        if name is not None:
            camp.name = name
        if status is not None:
            camp.status = status.upper()
        if daily_budget is not None:
            camp.daily_budget = daily_budget
        camp.updated_time = datetime.now(UTC).isoformat()
        return camp

    # ── Ad Sets ──────────────────────────────────────────────────────────────

    async def list_adsets(
        self,
        campaign_id: str | None = None,
    ) -> list[AdSet]:
        """List ad sets, optionally filtered by campaign ID."""
        adsets = list(self._adsets.values())
        if campaign_id:
            adsets = [a for a in adsets if a.campaign_id == campaign_id]
        return adsets

    async def get_adset(self, adset_id: str) -> AdSet:
        """Get an ad set by ID."""
        adset = self._adsets.get(adset_id)
        if not adset:
            raise ValueError(f"Ad set '{adset_id}' not found")
        return adset

    async def create_adset(
        self,
        campaign_id: str,
        name: str,
        targeting: dict[str, Any],
        daily_budget: float | None = None,
        status: str = "PAUSED",
        billing_event: str = "IMPRESSIONS",
        optimization_goal: str = "LINK_CLICKS",
    ) -> AdSet:
        """Create a new ad set targeting specific audiences and objectives."""
        adset_id = f"adset_{uuid4().hex[:9]}"
        now = datetime.now(UTC).isoformat()
        adset = AdSet(
            id=adset_id,
            campaign_id=campaign_id,
            name=name,
            status=status.upper(),
            daily_budget=daily_budget,
            billing_event=billing_event,
            optimization_goal=optimization_goal,
            targeting=targeting,
            start_time=now,
        )
        self._adsets[adset_id] = adset
        logger.info("Created Meta ad set %s (%s)", adset.name, adset.id)
        return adset

    async def update_adset(
        self,
        adset_id: str,
        status: str | None = None,
        daily_budget: float | None = None,
        targeting: dict[str, Any] | None = None,
    ) -> AdSet:
        """Update ad set status, budget, or targeting."""
        adset = await self.get_adset(adset_id)
        if status is not None:
            adset.status = status.upper()
        if daily_budget is not None:
            adset.daily_budget = daily_budget
        if targeting is not None:
            adset.targeting = targeting
        return adset

    # ── Creatives ────────────────────────────────────────────────────────────

    async def list_creatives(self, account_id: str | None = None) -> list[AdCreative]:
        """List creatives, optionally filtered by account ID."""
        creatives = list(self._creatives.values())
        if account_id:
            creatives = [c for c in creatives if c.account_id == account_id]
        return creatives

    async def get_creative(self, creative_id: str) -> AdCreative:
        """Get ad creative by ID."""
        cr = self._creatives.get(creative_id)
        if not cr:
            raise ValueError(f"Ad creative '{creative_id}' not found")
        return cr

    async def create_creative(
        self,
        account_id: str,
        name: str,
        title: str,
        body: str,
        image_url: str | None = None,
        link_url: str | None = None,
        call_to_action_type: str = "LEARN_MORE",
    ) -> AdCreative:
        """Create a new ad creative asset."""
        cr_id = f"cr_{uuid4().hex[:9]}"
        creative = AdCreative(
            id=cr_id,
            account_id=account_id,
            name=name,
            title=title,
            body=body,
            image_url=image_url or "https://images.unsplash.com/photo-1460925895917-afdab827c52f",
            link_url=link_url or "https://ceo-os.internal",
            call_to_action_type=call_to_action_type,
        )
        self._creatives[cr_id] = creative
        logger.info("Created Meta ad creative %s (%s)", creative.name, creative.id)
        return creative

    # ── Ads ──────────────────────────────────────────────────────────────────

    async def list_ads(
        self,
        adset_id: str | None = None,
    ) -> list[Ad]:
        """List ads, optionally filtered by ad set ID."""
        ads = list(self._ads.values())
        if adset_id:
            ads = [a for a in ads if a.adset_id == adset_id]
        return ads

    async def get_ad(self, ad_id: str) -> Ad:
        """Get ad by ID."""
        ad = self._ads.get(ad_id)
        if not ad:
            raise ValueError(f"Ad '{ad_id}' not found")
        return ad

    async def create_ad(
        self,
        adset_id: str,
        name: str,
        creative_id: str,
        status: str = "PAUSED",
    ) -> Ad:
        """Create a new ad linking a creative with an ad set."""
        ad_id = f"ad_{uuid4().hex[:9]}"
        now = datetime.now(UTC).isoformat()
        ad = Ad(
            id=ad_id,
            adset_id=adset_id,
            name=name,
            creative_id=creative_id,
            status=status.upper(),
            created_time=now,
        )
        self._ads[ad_id] = ad
        logger.info("Created Meta ad %s (%s)", ad.name, ad.id)
        return ad

    # ── Insights & Reporting ─────────────────────────────────────────────────

    async def get_insights(
        self,
        entity_id: str,
        entity_type: str = "campaign",
        date_preset: str = "last_30d",
    ) -> list[AdInsight]:
        """Fetch performance insights for a campaign, ad set, or account."""
        del date_preset
        if entity_id in self._insights:
            return self._insights[entity_id]

        # Generate realistic default insights based on entity
        camp = self._campaigns.get(entity_id)
        budget = camp.daily_budget if camp and camp.daily_budget else 800.0
        spend = budget * 14.0
        clicks = int(spend / 8.5)
        impressions = int(clicks * 30.5)
        ctr = round((clicks / impressions) * 100, 2)
        cpc = round(spend / clicks, 2)
        cpm = round((spend / impressions) * 1000, 2)
        conversions = int(clicks * 0.06)

        insight = AdInsight(
            entity_id=entity_id,
            entity_type=entity_type,
            date_start="2026-08-01",
            date_stop="2026-08-16",
            impressions=impressions,
            clicks=clicks,
            spend=spend,
            cpc=cpc,
            cpm=cpm,
            ctr=ctr,
            conversions=conversions,
            roas=3.2,
        )
        self._insights[entity_id] = [insight]
        return [insight]

    async def generate_report(self, campaign_id: str) -> CampaignReport:
        """Generate a complete executive report for a given campaign."""
        camp = await self.get_campaign(campaign_id)
        acc = await self.get_ad_account(camp.account_id)
        insights = await self.get_insights(campaign_id, entity_type="campaign")
        ins = insights[0] if insights else AdInsight(campaign_id, "campaign", "", "")

        currency_symbol = "₹" if acc.currency == "INR" else "$"
        summary = (
            f"Campaign '{camp.name}' ({camp.status}) has spent {currency_symbol}{ins.spend:,.2f} "
            f"generating {ins.impressions:,} impressions, {ins.clicks:,} clicks (CTR: {ins.ctr}%), "
            f"and {ins.conversions} conversions with ROAS {ins.roas}x."
        )

        return CampaignReport(
            account_id=camp.account_id,
            campaign_id=camp.id,
            campaign_name=camp.name,
            status=camp.status,
            daily_budget=camp.daily_budget or 0.0,
            currency=acc.currency,
            total_spend=ins.spend,
            impressions=ins.impressions,
            clicks=ins.clicks,
            ctr=ins.ctr,
            cpc=ins.cpc,
            conversions=ins.conversions,
            roas=ins.roas,
            summary=summary,
            insights=insights,
        )
