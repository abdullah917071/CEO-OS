"""Marketing Intelligence package."""

from intelligence.marketing.contracts import (
    AdSpendMetric,
    AttributionPeriodComparison,
    CreativePerformance,
    CrmMetric,
    MarketingSnapshot,
    ProfitDiagnosticReport,
    SalesMetric,
    TrafficMetric,
)
from intelligence.marketing.engine import MarketingIntelligenceEngine
from intelligence.marketing.provider import MarketingIntelligenceIntegration
from intelligence.marketing.tools import (
    MarketingAttributionFunnelTool,
    MarketingCreativesAnalyzeTool,
    MarketingProfitDiagnoseTool,
    MarketingSnapshotGetTool,
)

__all__ = [
    "AdSpendMetric",
    "AttributionPeriodComparison",
    "CreativePerformance",
    "CrmMetric",
    "MarketingAttributionFunnelTool",
    "MarketingCreativesAnalyzeTool",
    "MarketingIntelligenceEngine",
    "MarketingIntelligenceIntegration",
    "MarketingProfitDiagnoseTool",
    "MarketingSnapshot",
    "MarketingSnapshotGetTool",
    "ProfitDiagnosticReport",
    "SalesMetric",
    "TrafficMetric",
]
