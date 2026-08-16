"""Meta Marketing capability tools for the CEO OS capability registry."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from integrations.meta.client import MetaClient


class MetaAccountsListTool:
    """List accessible Meta ad accounts."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.accounts.list",
            description="List all accessible Meta Ad Accounts and their balances",
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        accounts = await self._client.list_ad_accounts()
        return ToolResult(
            output=[dataclasses.asdict(a) for a in accounts],
            evidence=[f"Found {len(accounts)} Meta ad account(s)"],
        )


class MetaAccountsGetTool:
    """Get details for a specific Meta ad account."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.accounts.get",
            description="Get details, currency, and balance for a specific Meta Ad Account",
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "Meta ad account ID"},
                },
                "required": ["account_id"],
            },
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        account_id = str(arguments["account_id"])
        acc = await self._client.get_ad_account(account_id)
        return ToolResult(
            output=dataclasses.asdict(acc),
            evidence=[f"Retrieved ad account {acc.name} ({acc.id}) - Currency: {acc.currency}"],
        )


class MetaCampaignsListTool:
    """List advertising campaigns."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.campaigns.list",
            description="List Meta advertising campaigns with status and budget details",
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Optional ad account ID filter",
                    },
                    "status": {"type": "string", "description": "Optional status filter"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        acc_id = arguments.get("account_id")
        status = arguments.get("status")
        campaigns = await self._client.list_campaigns(account_id=acc_id, status_filter=status)
        return ToolResult(
            output=[dataclasses.asdict(c) for c in campaigns],
            evidence=[f"Found {len(campaigns)} campaign(s) in Meta"],
        )


class MetaCampaignsCreateTool:
    """Create a new advertising campaign in Meta."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.campaigns.create",
            description="Create a new advertising campaign on Meta",
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Ad account ID to create under",
                    },
                    "name": {"type": "string", "description": "Campaign name"},
                    "objective": {
                        "type": "string",
                        "description": "Campaign objective (e.g. OUTCOME_TRAFFIC, OUTCOME_SALES)",
                        "default": "OUTCOME_TRAFFIC",
                    },
                    "status": {
                        "type": "string",
                        "description": "Initial campaign status (PAUSED | ACTIVE | DRAFT)",
                        "default": "PAUSED",
                    },
                    "daily_budget": {
                        "type": "number",
                        "description": "Daily budget amount in account currency",
                    },
                },
                "required": ["account_id", "name"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        acc_id = str(arguments["account_id"])
        name = str(arguments["name"])
        objective = str(arguments.get("objective", "OUTCOME_TRAFFIC"))
        status = str(arguments.get("status", "PAUSED"))
        daily_budget = float(arguments["daily_budget"]) if "daily_budget" in arguments else None

        camp = await self._client.create_campaign(
            account_id=acc_id,
            name=name,
            objective=objective,
            status=status,
            daily_budget=daily_budget,
        )
        return ToolResult(
            output=dataclasses.asdict(camp),
            evidence=[
                f"Created Meta campaign '{camp.name}' ({camp.id}) with status '{camp.status}' "
                f"and daily budget {camp.daily_budget or 'unset'}"
            ],
        )


class MetaCampaignsUpdateTool:
    """Update a Meta advertising campaign."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.campaigns.update",
            description="Update a Meta campaign status, budget, or name",
            input_schema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID to update"},
                    "status": {"type": "string", "description": "New status (ACTIVE | PAUSED)"},
                    "daily_budget": {"type": "number", "description": "New daily budget"},
                    "name": {"type": "string", "description": "New campaign name"},
                },
                "required": ["campaign_id"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        camp_id = str(arguments["campaign_id"])
        status = arguments.get("status")
        daily_budget = float(arguments["daily_budget"]) if "daily_budget" in arguments else None
        name = arguments.get("name")

        camp = await self._client.update_campaign(
            campaign_id=camp_id,
            name=name,
            status=status,
            daily_budget=daily_budget,
        )
        return ToolResult(
            output=dataclasses.asdict(camp),
            evidence=[f"Updated Meta campaign '{camp.name}' ({camp.id}) to status '{camp.status}'"],
        )


class MetaAdSetsListTool:
    """List ad sets for a campaign."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.adsets.list",
            description="List Meta ad sets with audience targeting and budget details",
            input_schema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Optional campaign filter"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        camp_id = arguments.get("campaign_id")
        adsets = await self._client.list_adsets(campaign_id=camp_id)
        return ToolResult(
            output=[dataclasses.asdict(a) for a in adsets],
            evidence=[f"Found {len(adsets)} ad set(s) in Meta"],
        )


class MetaAdSetsCreateTool:
    """Create a new ad set with targeting in Meta."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.adsets.create",
            description="Create an ad set with targeting parameters and budget in Meta",
            input_schema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Parent campaign ID"},
                    "name": {"type": "string", "description": "Ad set name"},
                    "targeting": {
                        "type": "object",
                        "description": "Targeting dictionary (geo, interests, age, etc.)",
                    },
                    "daily_budget": {"type": "number", "description": "Daily budget"},
                    "status": {"type": "string", "default": "PAUSED"},
                },
                "required": ["campaign_id", "name"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        camp_id = str(arguments["campaign_id"])
        name = str(arguments["name"])
        targeting = dict(arguments.get("targeting", {}))
        daily_budget = float(arguments["daily_budget"]) if "daily_budget" in arguments else None
        status = str(arguments.get("status", "PAUSED"))

        adset = await self._client.create_adset(
            campaign_id=camp_id,
            name=name,
            targeting=targeting,
            daily_budget=daily_budget,
            status=status,
        )
        return ToolResult(
            output=dataclasses.asdict(adset),
            evidence=[
                f"Created Meta ad set '{adset.name}' ({adset.id}) targeting specified audiences"
            ],
        )


class MetaCreativesListTool:
    """List ad creatives."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.creatives.list",
            description="List Meta ad creatives including headlines, copy, and media",
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "Optional ad account filter"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        acc_id = arguments.get("account_id")
        creatives = await self._client.list_creatives(account_id=acc_id)
        return ToolResult(
            output=[dataclasses.asdict(c) for c in creatives],
            evidence=[f"Found {len(creatives)} ad creative(s) in Meta"],
        )


class MetaCreativesCreateTool:
    """Create a new ad creative."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.creatives.create",
            description="Create an ad creative asset with headline, body copy, and media",
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "Ad account ID"},
                    "name": {"type": "string", "description": "Creative name"},
                    "title": {"type": "string", "description": "Ad headline"},
                    "body": {"type": "string", "description": "Ad body text"},
                    "image_url": {"type": "string", "description": "Image asset URL"},
                    "link_url": {"type": "string", "description": "Destination link URL"},
                    "call_to_action_type": {
                        "type": "string",
                        "description": "Call to action button (LEARN_MORE, SIGN_UP, SHOP_NOW)",
                        "default": "LEARN_MORE",
                    },
                },
                "required": ["account_id", "name", "title", "body"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        acc_id = str(arguments["account_id"])
        name = str(arguments["name"])
        title = str(arguments["title"])
        body = str(arguments["body"])
        img = arguments.get("image_url")
        link = arguments.get("link_url")
        cta = str(arguments.get("call_to_action_type", "LEARN_MORE"))

        cr = await self._client.create_creative(
            account_id=acc_id,
            name=name,
            title=title,
            body=body,
            image_url=img,
            link_url=link,
            call_to_action_type=cta,
        )
        return ToolResult(
            output=dataclasses.asdict(cr),
            evidence=[f"Created Meta ad creative '{cr.name}' ({cr.id}) with headline '{cr.title}'"],
        )


class MetaAdsListTool:
    """List ads in Meta."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.ads.list",
            description="List ads linking creatives to ad sets in Meta",
            input_schema={
                "type": "object",
                "properties": {
                    "adset_id": {"type": "string", "description": "Optional ad set filter"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        adset_id = arguments.get("adset_id")
        ads = await self._client.list_ads(adset_id=adset_id)
        return ToolResult(
            output=[dataclasses.asdict(a) for a in ads],
            evidence=[f"Found {len(ads)} ad(s) in Meta"],
        )


class MetaAdsCreateTool:
    """Create a new ad."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.ads.create",
            description="Create an ad linking a creative asset to an ad set in Meta",
            input_schema={
                "type": "object",
                "properties": {
                    "adset_id": {"type": "string", "description": "Target ad set ID"},
                    "name": {"type": "string", "description": "Ad name"},
                    "creative_id": {"type": "string", "description": "Creative asset ID"},
                    "status": {"type": "string", "default": "PAUSED"},
                },
                "required": ["adset_id", "name", "creative_id"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        adset_id = str(arguments["adset_id"])
        name = str(arguments["name"])
        creative_id = str(arguments["creative_id"])
        status = str(arguments.get("status", "PAUSED"))

        ad = await self._client.create_ad(
            adset_id=adset_id,
            name=name,
            creative_id=creative_id,
            status=status,
        )
        return ToolResult(
            output=dataclasses.asdict(ad),
            evidence=[f"Created Meta ad '{ad.name}' ({ad.id}) with status '{ad.status}'"],
        )


class MetaInsightsGetTool:
    """Get performance insights from Meta."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.insights.get",
            description=(
                "Fetch advertising performance metrics (spend, impressions, clicks, CTR, ROAS)"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Campaign, AdSet, or Account ID",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "campaign | adset | account",
                        "default": "campaign",
                    },
                },
                "required": ["entity_id"],
            },
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        entity_id = str(arguments["entity_id"])
        entity_type = str(arguments.get("entity_type", "campaign"))

        insights = await self._client.get_insights(entity_id=entity_id, entity_type=entity_type)
        ins = insights[0] if insights else None
        evidence = (
            [
                f"Meta insights for {entity_id}: Spend={ins.spend}, Clicks={ins.clicks}, "
                f"CTR={ins.ctr}%, ROAS={ins.roas}x"
            ]
            if ins
            else ["No insights returned"]
        )
        return ToolResult(
            output=[dataclasses.asdict(i) for i in insights],
            evidence=evidence,
        )


class MetaReportingCampaignTool:
    """Generate a comprehensive campaign performance report."""

    def __init__(self, client: MetaClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="meta.reporting.campaign",
            description="Generate executive performance summary report for a Meta campaign",
            input_schema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID to summarize"},
                },
                "required": ["campaign_id"],
            },
            risk=RiskLevel.READ,
            source="integration:meta",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        campaign_id = str(arguments["campaign_id"])
        report = await self._client.generate_report(campaign_id)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[f"Meta Campaign Report: {report.summary}"],
        )
