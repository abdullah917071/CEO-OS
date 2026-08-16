"""Native integration provider for Garry Tan's gstack virtual engineering team."""

from __future__ import annotations

from core.contracts import RiskLevel, Tool
from gstack.engine import GstackEngine
from gstack.tools import (
    GstackCeoReviewTool,
    GstackEngReviewTool,
    GstackOfficeHoursTool,
    GstackPipelineRunTool,
    GstackQaBrowserTool,
    GstackReleaseShipTool,
    GstackStaffReviewTool,
)
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider


class GstackIntegration(NativeIntegrationProvider):
    """Native integration provider connecting Garry Tan's gstack suite into CEO OS."""

    def __init__(self, engine: GstackEngine | None = None) -> None:
        super().__init__()
        self._engine = engine or GstackEngine()

    @property
    def engine(self) -> GstackEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        desc = (
            "Deep integration of Garry Tan's gstack virtual engineering team: "
            "Office Hours, CEO Review, Eng Review, Design Review, Staff Code Audit, "
            "QA Browser, and Ship"
        )
        return IntegrationManifest(
            name="gstack_engine",
            version="1.0.0",
            description=desc,
            integration_type=IntegrationType.NATIVE,
            domain="gstack",
            capabilities=[],
            required_credentials=[],
            rate_limits={"requests_per_minute": 300, "burst_limit": 50},
            risk_ceiling=RiskLevel.HARMLESS_WRITE,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [
            GstackOfficeHoursTool(self._engine),
            GstackCeoReviewTool(self._engine),
            GstackEngReviewTool(self._engine),
            GstackStaffReviewTool(self._engine),
            GstackQaBrowserTool(self._engine),
            GstackReleaseShipTool(self._engine),
            GstackPipelineRunTool(self._engine),
        ]
