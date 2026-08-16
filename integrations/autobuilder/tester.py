"""Automated sandbox test suite generator and runner for generated API integrations."""

from __future__ import annotations

import logging
import time
from typing import Any

from core.contracts import Tool
from integrations.autobuilder.contracts import (
    ApiEndpointSpec,
    ApiSpecification,
    ApiTestCase,
    ApiTestReport,
)

logger = logging.getLogger(__name__)


def _generate_sample_value(schema_prop: dict[str, Any], key: str) -> Any:
    """Synthesize a representative sample value from a JSON schema definition."""
    ptype = schema_prop.get("type", "string")
    if ptype == "string":
        if "email" in key.lower():
            return "test_user@example.com"
        if "id" in key.lower():
            return "sample_id_123"
        return f"sample_{key}"
    if ptype in ("integer", "number"):
        return 100
    if ptype == "boolean":
        return True
    if ptype == "array":
        return ["sample_item"]
    if ptype == "object":
        return {"sample_field": "sample_value"}
    return "sample_value"


class ApiIntegrationTester:
    """Sandbox testing and dry-run verification for auto-built API integrations."""

    def generate_test_cases(self, endpoint: ApiEndpointSpec) -> list[ApiTestCase]:
        """Generate positive test cases from endpoint parameter schema."""
        props = endpoint.parameters_schema.get("properties", {})
        sample_input: dict[str, Any] = {}

        for k, v in props.items():
            if isinstance(v, dict):
                sample_input[k] = _generate_sample_value(v, k)
            else:
                sample_input[k] = f"sample_{k}"

        return [
            ApiTestCase(
                test_id=f"test_{endpoint.operation_id}",
                operation_id=endpoint.operation_id,
                tool_name=endpoint.tool_name,
                input_sample=sample_input,
                expected_status=200,
                description=(
                    f"Validate {endpoint.method} {endpoint.path} with synthetic schema inputs"
                ),
            )
        ]

    async def run_tests(
        self,
        api_spec: ApiSpecification,
        tools: list[Tool],
    ) -> ApiTestReport:
        """Execute automated sandbox verification on all tools in the generated integration."""
        results: list[dict[str, Any]] = []
        passed_count = 0
        failed_count = 0

        tools_by_name = {t.spec.name: t for t in tools}

        for ep in api_spec.endpoints:
            test_cases = self.generate_test_cases(ep)
            for tc in test_cases:
                start = time.perf_counter()
                tool = tools_by_name.get(ep.tool_name)
                if not tool:
                    failed_count += 1
                    results.append(
                        {
                            "test_id": tc.test_id,
                            "tool_name": tc.tool_name,
                            "passed": False,
                            "error": f"Tool '{tc.tool_name}' not generated",
                            "duration_ms": 0.0,
                        }
                    )
                    continue

                try:
                    res = await tool.execute(tc.input_sample)
                    duration = round((time.perf_counter() - start) * 1000.0, 2)
                    if res.output and res.evidence:
                        passed_count += 1
                        results.append(
                            {
                                "test_id": tc.test_id,
                                "tool_name": tc.tool_name,
                                "passed": True,
                                "duration_ms": duration,
                                "evidence_count": len(res.evidence),
                            }
                        )
                    else:
                        failed_count += 1
                        results.append(
                            {
                                "test_id": tc.test_id,
                                "tool_name": tc.tool_name,
                                "passed": False,
                                "error": "Tool returned empty output or evidence",
                                "duration_ms": duration,
                            }
                        )
                except Exception as exc:
                    duration = round((time.perf_counter() - start) * 1000.0, 2)
                    failed_count += 1
                    logger.exception("Sandbox test '%s' failed", tc.test_id)
                    results.append(
                        {
                            "test_id": tc.test_id,
                            "tool_name": tc.tool_name,
                            "passed": False,
                            "error": str(exc),
                            "duration_ms": duration,
                        }
                    )

        total = passed_count + failed_count
        overall_passed = failed_count == 0 and total > 0

        return ApiTestReport(
            service_name=api_spec.service_name,
            passed=overall_passed,
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed_count,
            results=results,
        )
