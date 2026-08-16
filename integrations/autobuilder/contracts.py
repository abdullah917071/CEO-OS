"""Data contracts and schemas for the automated API ingestion and integration builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.contracts import RiskLevel
from integrations.contracts import IntegrationManifest


@dataclass(frozen=True, slots=True)
class ApiEndpointSpec:
    """Specification of an individual HTTP operation in an API."""

    operation_id: str
    tool_name: str
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    summary: str
    description: str = ""
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    request_body_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.READ
    requires_auth: bool = True


@dataclass(slots=True)
class ApiSpecification:
    """Normalized structured API specification parsed from OpenAPI, Swagger, or docs."""

    service_name: str
    title: str
    version: str
    base_url: str
    description: str = ""
    auth_type: str = "bearer"  # bearer, apikey_header, apikey_query, basic, none
    auth_key_or_header: str = "Authorization"
    endpoints: list[ApiEndpointSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ApiTestCase:
    """Automated sandbox test case for a generated API capability."""

    test_id: str
    operation_id: str
    tool_name: str
    input_sample: dict[str, Any]
    expected_status: int = 200
    description: str = ""


@dataclass(frozen=True, slots=True)
class ApiTestReport:
    """Outcome of running test cases on generated API tools."""

    service_name: str
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    results: list[dict[str, Any]]
    tested_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(slots=True)
class ApiBuildResult:
    """Result of building and registering an integration from API docs/spec."""

    service_name: str
    title: str
    version: str
    base_url: str
    tools_generated_count: int
    tool_names: list[str]
    tests_passed: bool
    registered: bool
    manifest: IntegrationManifest
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
