"""API Auto-Builder subsystem (introduced in Phase 19)."""

from integrations.autobuilder.contracts import (
    ApiBuildResult,
    ApiEndpointSpec,
    ApiSpecification,
    ApiTestCase,
    ApiTestReport,
)
from integrations.autobuilder.engine import ApiAutoBuilderEngine
from integrations.autobuilder.generator import (
    DynamicApiIntegrationProvider,
    DynamicApiTool,
)
from integrations.autobuilder.integration import ApiAutoBuilderIntegration
from integrations.autobuilder.parser import OpenApiParser
from integrations.autobuilder.tester import ApiIntegrationTester
from integrations.autobuilder.tools import (
    ApiIngestTool,
    ApiInspectTool,
    ApiListTool,
    ApiTestTool,
)

__all__ = [
    "ApiAutoBuilderEngine",
    "ApiAutoBuilderIntegration",
    "ApiBuildResult",
    "ApiEndpointSpec",
    "ApiIngestTool",
    "ApiInspectTool",
    "ApiIntegrationTester",
    "ApiListTool",
    "ApiSpecification",
    "ApiTestCase",
    "ApiTestReport",
    "ApiTestTool",
    "DynamicApiIntegrationProvider",
    "DynamicApiTool",
    "OpenApiParser",
]
