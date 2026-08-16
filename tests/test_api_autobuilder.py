import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.capabilities import CapabilityRegistry
from core.contracts import RiskLevel
from integrations.autobuilder.engine import ApiAutoBuilderEngine
from integrations.autobuilder.generator import DynamicApiIntegrationProvider
from integrations.autobuilder.integration import ApiAutoBuilderIntegration
from integrations.autobuilder.parser import OpenApiParser
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.registry import IntegrationRegistry
from integrations.router import CapabilityRouter


def test_autobuilder_manifest_and_tool_registration() -> None:
    integration = ApiAutoBuilderIntegration()
    manifest = integration.manifest()

    assert manifest.name == "api_auto_builder"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.risk_ceiling == RiskLevel.HARMLESS_WRITE

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 4
    tool_names = {t.spec.name for t in tools}
    expected = {
        "developer.api.ingest",
        "developer.api.test",
        "developer.api.inspect",
        "developer.api.list",
    }
    assert expected == tool_names


def test_openapi_parser_full_spec() -> None:
    parser = OpenApiParser()
    sample_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Airtable Integration API",
            "version": "2.1.0",
            "description": "Programmatic database interface for Airtable bases.",
        },
        "servers": [{"url": "https://api.airtable.com/v0"}],
        "components": {
            "securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}},
            "schemas": {
                "Record": {
                    "type": "object",
                    "required": ["fields"],
                    "properties": {
                        "id": {"type": "string"},
                        "fields": {"type": "object"},
                    },
                }
            },
        },
        "paths": {
            "/bases/{base_id}/records": {
                "get": {
                    "operationId": "list_records",
                    "summary": "List Records in Base",
                    "parameters": [
                        {
                            "name": "base_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"name": "max_records", "in": "query", "schema": {"type": "integer"}},
                    ],
                },
                "post": {
                    "operationId": "create_record",
                    "summary": "Create Record in Base",
                    "parameters": [
                        {
                            "name": "base_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Record"}}
                        }
                    },
                },
            },
            "/bases/{base_id}/records/{record_id}": {
                "delete": {
                    "operationId": "delete_record",
                    "summary": "Delete Record from Base",
                    "parameters": [
                        {
                            "name": "base_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "record_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                }
            },
        },
    }

    api_spec = parser.parse(sample_spec)
    assert api_spec.service_name == "airtable_integration_api"
    assert api_spec.version == "2.1.0"
    assert api_spec.base_url == "https://api.airtable.com/v0"
    assert api_spec.auth_type == "bearer"
    assert len(api_spec.endpoints) == 3

    # Check endpoints & inferred risk levels
    ep_by_id = {ep.operation_id: ep for ep in api_spec.endpoints}

    list_ep = ep_by_id["list_records"]
    assert list_ep.method == "GET"
    assert list_ep.risk_level == RiskLevel.READ
    assert list_ep.tool_name == "airtable_integration_api.records.list"
    assert "base_id" in list_ep.parameters_schema.get("required", [])

    create_ep = ep_by_id["create_record"]
    assert create_ep.method == "POST"
    assert create_ep.risk_level == RiskLevel.HARMLESS_WRITE
    assert create_ep.tool_name == "airtable_integration_api.records.create"
    assert "fields" in create_ep.parameters_schema.get("properties", {})

    del_ep = ep_by_id["delete_record"]
    assert del_ep.method == "DELETE"
    assert del_ep.risk_level == RiskLevel.BUSINESS_CHANGE
    assert del_ep.tool_name == "airtable_integration_api.records.delete"


@pytest.mark.asyncio
async def test_dynamic_tool_and_provider_generation() -> None:
    parser = OpenApiParser()
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Linear", "version": "1.0.0"},
        "servers": [{"url": "https://api.linear.app/graphql"}],
        "paths": {
            "/issues/{issue_id}": {
                "get": {
                    "operationId": "get_issue",
                    "summary": "Get Issue Details",
                    "parameters": [{"name": "issue_id", "in": "path", "required": True}],
                }
            },
            "/issues": {
                "post": {
                    "operationId": "create_issue",
                    "summary": "Create New Issue",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "team_id": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                }
            },
        },
    }

    api_spec = parser.parse(spec, service_name_override="linear")
    provider = DynamicApiIntegrationProvider(api_spec)
    assert provider.manifest().name == "linear"

    tools = provider.build_tools()
    assert len(tools) == 2
    tools_map = {t.spec.name: t for t in tools}

    get_tool = tools_map["linear.issues.get"]
    get_res = await get_tool.execute({"issue_id": "LIN-404"})
    assert get_res.output["status"] == "success"
    assert get_res.output["endpoint"] == "GET /issues/LIN-404"

    create_tool = tools_map["linear.issues.create"]
    create_res = await create_tool.execute({"title": "Implement API builder", "team_id": "eng"})
    assert create_res.output["status"] == "success"
    assert create_res.output["title"] == "Implement API builder"
    assert create_res.output["team_id"] == "eng"


@pytest.mark.asyncio
async def test_autobuilder_engine_end_to_end_with_registry_sync() -> None:
    registry = IntegrationRegistry()
    engine = ApiAutoBuilderEngine(integration_registry=registry)

    # Listeners for capability registry synchronization
    cap_registry = CapabilityRegistry([])

    def _sync(r: IntegrationRegistry) -> None:
        for t in r.all_tools():
            cap_registry.register(t)

    registry.add_listener(_sync)

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Stripe Payments", "version": "2024-06-20"},
        "servers": [{"url": "https://api.stripe.com/v1"}],
        "paths": {
            "/charges": {
                "post": {
                    "operationId": "create_charge",
                    "summary": "Create Customer Charge",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["amount", "currency"],
                                    "properties": {
                                        "amount": {"type": "integer"},
                                        "currency": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                }
            }
        },
    }

    build_res, test_report = await engine.ingest_and_build(
        raw_spec=spec,
        service_name_override="stripe",
        auto_register=True,
    )

    assert build_res.service_name == "stripe"
    assert build_res.registered is True
    assert build_res.tests_passed is True
    assert test_report.passed is True
    assert len(build_res.tool_names) == 1
    assert "stripe.charges.create" in build_res.tool_names

    # Check live capability registry synchronization
    assert cap_registry.has("stripe.charges.create")
    charge_tool = cap_registry.get("stripe.charges.create")
    res = await charge_tool.execute({"amount": 5000, "currency": "inr"})
    assert res.output["status"] == "success"
    assert res.output["amount"] == 5000


def test_capability_router_developer_autobuilder_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains(
        "Developer Agent, ingest OpenAPI specification for Notion API"
    )
    assert "integrations" in domains

    doc_domains = router.classify_domains("Generate API capabilities from swagger documentation")
    assert "integrations" in doc_domains


def test_api_autobuilder_endpoints() -> None:
    with TestClient(app) as client:
        # 1. Ingest API spec
        spec_payload = {
            "spec": {
                "openapi": "3.0.0",
                "info": {"title": "PostHog Analytics", "version": "1.2.0"},
                "servers": [{"url": "https://app.posthog.com/api"}],
                "paths": {
                    "/events": {
                        "post": {
                            "operationId": "capture_event",
                            "summary": "Capture Analytics Event",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["event"],
                                            "properties": {
                                                "event": {"type": "string"},
                                                "properties": {"type": "object"},
                                            },
                                        }
                                    }
                                }
                            },
                        }
                    }
                },
            },
            "service_name": "posthog",
            "auto_register": True,
        }

        ingest_resp = client.post("/api/v1/integrations/autobuilder/ingest", json=spec_payload)
        assert ingest_resp.status_code == 201
        data = ingest_resp.json()
        assert data["service_name"] == "posthog"
        assert data["registered"] is True
        assert data["tools_generated_count"] == 1
        assert "posthog.events.create" in data["tool_names"]

        # 2. List auto-built integrations
        list_resp = client.get("/api/v1/integrations/autobuilder/integrations")
        assert list_resp.status_code == 200
        integrations_list = list_resp.json()
        assert any(i["service_name"] == "posthog" for i in integrations_list)

        # 3. Inspect auto-built integration
        inspect_resp = client.get("/api/v1/integrations/autobuilder/integrations/posthog")
        assert inspect_resp.status_code == 200
        inspect_data = inspect_resp.json()
        assert inspect_data["service_name"] == "posthog"
        assert len(inspect_data["endpoints"]) == 1

        # 4. Test auto-built integration
        test_resp = client.post("/api/v1/integrations/autobuilder/integrations/posthog/test")
        assert test_resp.status_code == 200
        assert test_resp.json()["passed"] is True


def test_api_autobuilder_acceptance_scenario() -> None:
    """Roadmap Acceptance Test for Phase 19:

    'Developer Agent, ingest the OpenAPI specification for Linear
    and register its capabilities.'
    """
    with TestClient(app) as client:
        message = (
            "Developer Agent, ingest the OpenAPI specification for linear "
            "and register its capabilities"
        )
        resp = client.post("/api/v1/chat/messages", json={"message": message})
        assert resp.status_code == 202
        task_id = resp.json()["id"]

        deadline = time.time() + 10.0
        task: dict[str, object] = {}
        while time.time() < deadline:
            task_resp = client.get(f"/api/v1/tasks/{task_id}")
            assert task_resp.status_code == 200
            task = task_resp.json()
            if task["status"] in {"success", "failed", "cancelled"}:
                break
            time.sleep(0.1)

        assert task["status"] == "success", f"Task failed with error: {task.get('error')}"
        plan = task.get("plan", {})
        assert isinstance(plan, dict)
        steps = plan.get("steps", [])
        assert len(steps) >= 1
        assert steps[0]["capability"] == "developer.api.ingest"

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        evidence_str = " ".join(str(e).lower() for e in evidence)
        assert "auto-generated integration" in evidence_str
        assert "linear" in evidence_str
        assert "active in capabilityregistry" in evidence_str
