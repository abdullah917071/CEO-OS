"""Native Integration Provider for the Skills Engine."""

from __future__ import annotations

from typing import Any

from core.contracts import RiskLevel, Tool
from integrations.contracts import IntegrationManifest, IntegrationType
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker
from skills.engine import SkillsEngine
from skills.tools import (
    SkillCreateTool,
    SkillDisableTool,
    SkillExecuteTool,
    SkillGetTool,
    SkillListTool,
    SkillTestTool,
    SkillVersionTool,
)


class SkillsIntegration(NativeIntegrationProvider):
    """Native integration for procedural skill execution, testing, and versioning."""

    def __init__(
        self,
        engine: SkillsEngine | None = None,
        registry_getter: Any = None,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._engine = engine or SkillsEngine()
        self._registry_getter = registry_getter

    @property
    def engine(self) -> SkillsEngine:
        return self._engine

    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="skills_engine",
            version="1.0.0",
            description=(
                "Skills Engine: learned procedural workflows with creation, "
                "testing simulation, multi-step execution, and semantic versioning."
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.EXTERNAL_COMMUNICATION,
            enabled=True,
            rate_limits={"requests_per_minute": 120, "burst_limit": 30},
        )

    def build_tools(self) -> list[Tool]:
        return [
            SkillCreateTool(self._engine),
            SkillExecuteTool(self._engine, self._registry_getter),
            SkillTestTool(self._engine, self._registry_getter),
            SkillVersionTool(self._engine),
            SkillDisableTool(self._engine),
            SkillListTool(self._engine),
            SkillGetTool(self._engine),
        ]
