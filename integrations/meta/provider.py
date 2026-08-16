"""Native Integration Provider for the Meta Marketing API."""

from __future__ import annotations

from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.meta.client import MetaClient
from integrations.meta.tools import (
    MetaAccountsGetTool,
    MetaAccountsListTool,
    MetaAdsCreateTool,
    MetaAdSetsCreateTool,
    MetaAdSetsListTool,
    MetaAdsListTool,
    MetaCampaignsCreateTool,
    MetaCampaignsListTool,
    MetaCampaignsUpdateTool,
    MetaCreativesCreateTool,
    MetaCreativesListTool,
    MetaInsightsGetTool,
    MetaReportingCampaignTool,
)
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker


class MetaMarketingIntegration(NativeIntegrationProvider):
    """Meta Marketing API Native Integration Provider."""

    def __init__(
        self,
        client: MetaClient | None = None,
        secret_broker: SecretBroker | None = None,
        token_ref: str | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._client = client or MetaClient(secret_broker=secret_broker)
        self._token_ref = token_ref

    @property
    def client(self) -> MetaClient:
        return self._client

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="meta_marketing",
            version="1.0.0",
            description=(
                "Meta Marketing API integration for Facebook and Instagram advertising: "
                "Ad Accounts, Campaigns, Ad Sets, Creatives, Ads, Insights, and Reporting."
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.EXTERNAL_COMMUNICATION,
            required_credentials=[self._token_ref] if self._token_ref else [],
            enabled=True,
            rate_limits={"requests_per_minute": 120, "burst_limit": 20},
        )

    def build_tools(self) -> list[Tool]:
        return [
            MetaAccountsListTool(self._client),
            MetaAccountsGetTool(self._client),
            MetaCampaignsListTool(self._client),
            MetaCampaignsCreateTool(self._client),
            MetaCampaignsUpdateTool(self._client),
            MetaAdSetsListTool(self._client),
            MetaAdSetsCreateTool(self._client),
            MetaCreativesListTool(self._client),
            MetaCreativesCreateTool(self._client),
            MetaAdsListTool(self._client),
            MetaAdsCreateTool(self._client),
            MetaInsightsGetTool(self._client),
            MetaReportingCampaignTool(self._client),
        ]
