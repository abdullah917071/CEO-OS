"""API Auto-Builder Engine: ingestion, generation, testing, and live registration pipeline."""

from __future__ import annotations

import logging
from typing import Any

from integrations.autobuilder.contracts import (
    ApiBuildResult,
    ApiSpecification,
    ApiTestReport,
)
from integrations.autobuilder.generator import DynamicApiIntegrationProvider
from integrations.autobuilder.parser import OpenApiParser
from integrations.autobuilder.tester import ApiIntegrationTester
from integrations.registry import IntegrationRegistry
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)


class ApiAutoBuilderEngine:
    """Orchestrates API ingestion, capability generation, and live registration."""

    def __init__(
        self,
        integration_registry: IntegrationRegistry | None = None,
        secret_broker: SecretBroker | None = None,
    ) -> None:
        self._registry = integration_registry
        self._secret_broker = secret_broker
        self._parser = OpenApiParser()
        self._tester = ApiIntegrationTester()
        self._providers: dict[str, DynamicApiIntegrationProvider] = {}
        self._build_history: dict[str, ApiBuildResult] = {}

    def set_integration_registry(self, registry: IntegrationRegistry) -> None:
        self._registry = registry

    async def ingest_and_build(
        self,
        raw_spec: dict[str, Any] | str,
        service_name_override: str | None = None,
        base_url_override: str | None = None,
        auth_config: dict[str, Any] | None = None,
        auto_register: bool = True,
    ) -> tuple[ApiBuildResult, ApiTestReport]:
        """Ingest API specification, generate capabilities, test, and register."""
        # 1. Parse documentation or OpenAPI spec
        api_spec = self._parser.parse(
            raw_spec=raw_spec,
            service_name_override=service_name_override,
            base_url_override=base_url_override,
        )

        # 2. Generate dynamic provider and capability tools
        provider = DynamicApiIntegrationProvider(
            api_spec=api_spec,
            auth_config=auth_config,
            secret_broker=self._secret_broker,
        )
        tools = provider.build_tools()

        # 3. Sandbox testing
        test_report = await self._tester.run_tests(api_spec=api_spec, tools=tools)

        # 4. Live registration
        registered = False
        if test_report.passed and auto_register and self._registry is not None:
            await self._registry.install_native(provider)
            registered = True
            logger.info(
                "Registered auto-built API integration '%s' with %d capabilities",
                api_spec.service_name,
                len(tools),
            )

        manifest = provider.manifest()
        build_result = ApiBuildResult(
            service_name=api_spec.service_name,
            title=api_spec.title,
            version=api_spec.version,
            base_url=api_spec.base_url,
            tools_generated_count=len(tools),
            tool_names=[t.spec.name for t in tools],
            tests_passed=test_report.passed,
            registered=registered,
            manifest=manifest,
        )

        self._providers[api_spec.service_name] = provider
        self._build_history[api_spec.service_name] = build_result

        return build_result, test_report

    def get_api_spec(self, service_name: str) -> ApiSpecification:
        if service_name not in self._providers:
            raise KeyError(f"Auto-built API service '{service_name}' not found")
        return self._providers[service_name].api_spec

    def list_builds(self) -> list[ApiBuildResult]:
        return list(self._build_history.values())

    async def test_integration(self, service_name: str) -> ApiTestReport:
        if service_name not in self._providers:
            raise KeyError(f"Auto-built API service '{service_name}' not found")
        provider = self._providers[service_name]
        tools = provider.build_tools()
        return await self._tester.run_tests(api_spec=provider.api_spec, tools=tools)
