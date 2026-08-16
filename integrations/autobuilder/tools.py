"""Developer Agent capability tools for API specification ingestion and auto-building."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from integrations.autobuilder.engine import ApiAutoBuilderEngine


class ApiIngestTool:
    """Tool for Developer Agent to ingest an API specification and generate live capabilities."""

    def __init__(self, engine: ApiAutoBuilderEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="developer.api.ingest",
            description=(
                "Ingest OpenAPI specification or API docs, generate typed tools, "
                "run sandbox tests, and register capabilities"
            ),
            input_schema={
                "type": "object",
                "required": ["spec"],
                "properties": {
                    "spec": {
                        "type": "object",
                        "description": "OpenAPI JSON / Swagger object or string",
                    },
                    "service_name": {
                        "type": "string",
                        "description": "Optional service name override (e.g. 'linear', 'stripe')",
                    },
                    "base_url": {
                        "type": "string",
                        "description": "Optional base API URL override",
                    },
                    "auth_config": {
                        "type": "object",
                        "description": "Optional auth headers or API token",
                        "default": {},
                    },
                    "auto_register": {
                        "type": "boolean",
                        "description": "Whether to register capabilities upon test success",
                        "default": True,
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:developer_agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        raw_spec = arguments["spec"]
        service_name = arguments.get("service_name")
        base_url = arguments.get("base_url")
        auth_config = arguments.get("auth_config", {})
        auto_reg = bool(arguments.get("auto_register", True))

        build_res, test_rep = await self._engine.ingest_and_build(
            raw_spec=raw_spec,
            service_name_override=service_name,
            base_url_override=base_url,
            auth_config=auth_config,
            auto_register=auto_reg,
        )

        output = {
            "service_name": build_res.service_name,
            "title": build_res.title,
            "version": build_res.version,
            "base_url": build_res.base_url,
            "tools_generated_count": build_res.tools_generated_count,
            "tool_names": build_res.tool_names,
            "tests_passed": build_res.tests_passed,
            "registered": build_res.registered,
            "manifest": dataclasses.asdict(build_res.manifest),
            "test_summary": {
                "total_tests": test_rep.total_tests,
                "passed_tests": test_rep.passed_tests,
                "failed_tests": test_rep.failed_tests,
            },
        }

        tool_list = ", ".join(build_res.tool_names)
        reg_status = "ACTIVE in CapabilityRegistry" if build_res.registered else "DRAFT"
        evidence = [
            f"Auto-generated integration '{build_res.service_name}' (v{build_res.version})",
            f"Generated {build_res.tools_generated_count} tools: {tool_list}",
            f"Sandbox verification: {test_rep.passed_tests}/{test_rep.total_tests} passed",
            f"Registration status: {reg_status}",
        ]

        return ToolResult(output=output, evidence=evidence)


class ApiTestTool:
    """Tool to execute sandbox test verification on an auto-built API integration."""

    def __init__(self, engine: ApiAutoBuilderEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="developer.api.test",
            description="Run automated sandbox test suite against a generated API integration",
            input_schema={
                "type": "object",
                "required": ["service_name"],
                "properties": {
                    "service_name": {"type": "string", "description": "Name of the API service"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:developer_agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        service_name = str(arguments["service_name"])
        report = await self._engine.test_integration(service_name)
        status_label = "PASSED" if report.passed else "FAILED"

        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[
                f"API test for '{service_name}': "
                f"{report.passed_tests}/{report.total_tests} passed (Status: {status_label})"
            ],
        )


class ApiInspectTool:
    """Tool to inspect endpoints and schemas of an auto-built API integration."""

    def __init__(self, engine: ApiAutoBuilderEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="developer.api.inspect",
            description="Inspect endpoints, schemas, and capabilities of an auto-built API service",
            input_schema={
                "type": "object",
                "required": ["service_name"],
                "properties": {
                    "service_name": {"type": "string", "description": "Service name to inspect"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:developer_agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        service_name = str(arguments["service_name"])
        spec = self._engine.get_api_spec(service_name)

        return ToolResult(
            output=dataclasses.asdict(spec),
            evidence=[
                f"API service '{spec.service_name}' (v{spec.version}) has "
                f"{len(spec.endpoints)} endpoint(s) mapped to capabilities"
            ],
        )


class ApiListTool:
    """Tool to list all auto-built API integrations in the system."""

    def __init__(self, engine: ApiAutoBuilderEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="developer.api.list",
            description="List all auto-built API services and their registration status",
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.READ,
            source="integration:developer_agent",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        builds = self._engine.list_builds()

        return ToolResult(
            output=[dataclasses.asdict(b) for b in builds],
            evidence=[f"Found {len(builds)} auto-built API integration(s)"],
        )
