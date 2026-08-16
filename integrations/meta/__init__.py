"""Meta Marketing API integration package."""

from integrations.meta.client import MetaClient
from integrations.meta.contracts import (
    Ad,
    AdAccount,
    AdCreative,
    AdInsight,
    AdSet,
    Campaign,
    CampaignReport,
)
from integrations.meta.provider import MetaMarketingIntegration

__all__ = [
    "Ad",
    "AdAccount",
    "AdCreative",
    "AdInsight",
    "AdSet",
    "Campaign",
    "CampaignReport",
    "MetaClient",
    "MetaMarketingIntegration",
]
