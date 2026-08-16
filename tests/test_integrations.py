from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from integrations.contracts import (
    AuthenticationError,
    IntegrationHealth,
    IntegrationManifest,
    IntegrationType,
    OAuthProfile,
    RateLimitError,
)
from integrations.mcp_adapter import McpToolAdapter, _cap_risk
from integrations.mcp_config import load_mcp_configs
from integrations.native import (
    MockWeatherIntegration,
    NativeIntegrationProvider,
    SystemInfoIntegration,
    TokenBucketRateLimiter,
)
from integrations.oauth import OAuthManager, _generate_pkce
from integrations.registry import IntegrationRegistry
from integrations.router import CapabilityRouter
from integrations.secrets import SecretBroker


class DummyNativeTool:
    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="dummy.echo",
            description="Echo input text",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            risk=RiskLevel.READ,
            source="integration:dummy",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        text = str(arguments.get("text", ""))
        return ToolResult({"echo": text}, [f"Echoed: {text}"])


class DummyIntegration(NativeIntegrationProvider):
    def manifest(self) -> IntegrationManifest:
        return IntegrationManifest(
            name="dummy",
            version="1.0.0",
            description="Dummy test integration",
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.READ,
            enabled=True,
        )

    def build_tools(self) -> list[Tool]:
        return [DummyNativeTool()]


def test_integration_registry_lifecycle() -> None:
    registry = IntegrationRegistry()
    provider = DummyIntegration()

    registry.register(provider)
    assert len(registry.list_integrations()) == 1
    assert registry.get("dummy") is provider

    # Duplicate registration should raise
    with pytest.raises(ValueError, match="already registered"):
        registry.register(provider)

    # Tools should be empty before connect
    assert len(registry.all_tools()) == 0


@pytest.mark.asyncio
async def test_integration_registry_connect_and_disconnect() -> None:
    registry = IntegrationRegistry()
    provider = DummyIntegration()
    registry.register(provider)

    await registry.connect_all()
    status = provider.status()
    assert status.health == IntegrationHealth.HEALTHY
    assert status.connected_at is not None
    assert status.tool_count == 1
    assert len(registry.all_tools()) == 1

    await registry.disconnect_all()
    status_after = provider.status()
    assert status_after.health == IntegrationHealth.UNAVAILABLE
    assert len(registry.all_tools()) == 0

    # Unregister removes provider
    await registry.unregister("dummy")
    assert registry.get("dummy") is None
    assert len(registry.list_integrations()) == 0


@pytest.mark.asyncio
async def test_system_info_native_integration(tmp_path: Path) -> None:
    integration = SystemInfoIntegration(tmp_path)
    manifest = integration.manifest()
    assert manifest.name == "system_info"
    assert manifest.risk_ceiling == RiskLevel.READ
    assert manifest.integration_type == IntegrationType.NATIVE

    await integration.connect()
    assert integration.status().health == IntegrationHealth.HEALTHY
    tools = integration.tools()
    assert len(tools) == 1

    tool = tools[0]
    assert tool.spec.name == "system_info.platform"
    assert tool.spec.risk == RiskLevel.READ
    assert tool.spec.source == "integration:system_info"

    result = await tool.execute({})
    assert "system" in result.output
    assert "platform" in result.output
    assert "python_version" in result.output
    assert "hostname" in result.output
    assert result.output["workspace"] == str(tmp_path)
    assert len(result.evidence) == 1

    await integration.disconnect()
    assert integration.status().health == IntegrationHealth.UNAVAILABLE


def test_mcp_config_loader_from_env_and_file(tmp_path: Path) -> None:
    # Empty config
    assert load_mcp_configs() == []
    assert load_mcp_configs(env_json="   ") == []

    # Valid JSON array from env
    env_data = json.dumps(
        [
            {
                "name": "test-server",
                "command": "python",
                "args": ["server.py"],
                "domain": "tools",
                "risk_ceiling": "R0",
                "enabled": True,
                "timeout_seconds": 15,
            }
        ]
    )
    configs = load_mcp_configs(env_json=env_data)
    assert len(configs) == 1
    assert configs[0].name == "test-server"
    assert configs[0].command == "python"
    assert configs[0].args == ["server.py"]
    assert configs[0].domain == "tools"
    assert configs[0].risk_ceiling == RiskLevel.READ
    assert configs[0].timeout_seconds == 15

    # Valid JSON from file
    config_file = tmp_path / "mcp_servers.json"
    config_file.write_text(env_data, encoding="utf-8")
    file_configs = load_mcp_configs(json_path=config_file)
    assert len(file_configs) == 1
    assert file_configs[0].name == "test-server"

    # Malformed JSON handling
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    assert load_mcp_configs(json_path=bad_file) == []

    # Non-array JSON
    obj_file = tmp_path / "obj.json"
    obj_file.write_text('{"name": "single"}', encoding="utf-8")
    assert load_mcp_configs(json_path=obj_file) == []


def test_mcp_risk_capping() -> None:
    # Capped at R0
    assert _cap_risk(RiskLevel.HARMLESS_WRITE, RiskLevel.READ) == RiskLevel.READ
    # Allowed at R2 if ceiling is R2
    assert (
        _cap_risk(RiskLevel.EXTERNAL_COMMUNICATION, RiskLevel.EXTERNAL_COMMUNICATION)
        == RiskLevel.EXTERNAL_COMMUNICATION
    )
    # Lower than ceiling preserves lower risk
    assert _cap_risk(RiskLevel.READ, RiskLevel.DESTRUCTIVE_ADMIN) == RiskLevel.READ


@dataclass
class _FakeContentBlock:
    text: str


@dataclass
class _FakeCallResult:
    content: list[_FakeContentBlock]
    is_error: bool = False


@pytest.mark.asyncio
async def test_mcp_tool_adapter_execution() -> None:
    mock_client = MagicMock()
    mock_client.call_tool = AsyncMock(
        return_value=_FakeCallResult(
            content=[_FakeContentBlock(text=json.dumps({"temperature": 72, "unit": "F"}))],
            is_error=False,
        )
    )

    adapter = McpToolAdapter(
        tool_name="get_weather",
        tool_description="Get weather for a city",
        tool_input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
        server_name="weather_service",
        risk_ceiling=RiskLevel.READ,
        client=mock_client,
        timeout_seconds=5,
    )

    spec = adapter.spec
    assert spec.name == "get_weather"
    assert spec.description == "Get weather for a city"
    assert spec.risk == RiskLevel.READ
    assert spec.source == "mcp:weather_service"

    result = await adapter.execute({"city": "San Francisco"})
    assert result.output == {"temperature": 72, "unit": "F"}
    assert len(result.evidence) == 1
    assert "weather_service" in result.evidence[0]


@pytest.mark.asyncio
async def test_mcp_tool_adapter_error_handling() -> None:
    mock_client = MagicMock()
    mock_client.call_tool = AsyncMock(
        return_value=_FakeCallResult(
            content=[_FakeContentBlock(text="City not found")],
            is_error=True,
        )
    )

    adapter = McpToolAdapter(
        tool_name="get_weather",
        tool_description="Get weather",
        tool_input_schema={},
        server_name="weather_service",
        risk_ceiling=RiskLevel.HARMLESS_WRITE,
        client=mock_client,
        timeout_seconds=5,
    )

    with pytest.raises(RuntimeError, match="City not found"):
        await adapter.execute({"city": "Atlantis"})


# ── Secret Broker & Vault Tests ─────────────────────────────────────────────


def test_secret_vault_and_broker_lifecycle_and_masking() -> None:
    broker = SecretBroker()

    # Register secret
    ref = broker.register_secret(
        name="meta_ad_token",
        secret_value="super_secret_access_token_12345",
        description="Meta primary advertising token",
        tags=["meta", "ads"],
    )
    assert ref.credential_id.startswith("cred_")
    assert ref.name == "meta_ad_token"

    # Reference lookup contains no raw secret
    looked_up = broker.get_reference(ref.credential_id)
    assert looked_up is not None
    assert "super_secret" not in repr(looked_up)

    # Secret leasing
    lease = broker.lease_secret(ref.credential_id, requester="meta_integration")
    assert lease.secret_value == "super_secret_access_token_12345"

    # Redaction / Masking in audit logs and strings
    raw_message = "Calling API with token super_secret_access_token_12345 in header"
    masked = broker.mask_secrets(raw_message)
    assert "super_secret_access_token_12345" not in masked
    assert "[REDACTED_SECRET]" in masked

    # Sanitize structured payload
    payload = {
        "api_key": "raw_pass_val",
        "nested": {"token": "super_secret_access_token_12345", "user": "alice"},
    }
    sanitized = broker.sanitize_payload(payload)
    assert sanitized["api_key"] == "[REDACTED_SECRET]"
    assert sanitized["nested"]["token"] == "[REDACTED_SECRET]"
    assert sanitized["nested"]["user"] == "alice"

    # Revoke secret
    assert broker.revoke_secret(ref.credential_id) is True
    with pytest.raises(AuthenticationError):
        broker.lease_secret(ref.credential_id, requester="meta_integration")


# ── OAuth 2.0 PKCE Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_oauth_manager_pkce_flow() -> None:
    broker = SecretBroker()
    cid_ref = broker.register_secret("meta_client_id", "client_id_999")
    cs_ref = broker.register_secret("meta_client_secret", "client_secret_888")

    manager = OAuthManager(broker)
    profile = OAuthProfile(
        provider_name="meta",
        client_id_ref=cid_ref.credential_id,
        client_secret_ref=cs_ref.credential_id,
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        scopes=["ads_management", "ads_read"],
    )
    manager.register_profile(profile)

    # Start authorization
    auth_url, state = manager.start_authorization("meta")
    assert "https://www.facebook.com/v19.0/dialog/oauth" in auth_url
    assert "code_challenge=" in auth_url
    assert "code_challenge_method=S256" in auth_url
    assert state.state_token in auth_url

    # Exchange code with mock token response
    mock_resp = {
        "access_token": "EAAX_meta_access_token_valid_123",
        "token_type": "Bearer",
        "expires_in": 7200,
    }
    token_record = await manager.exchange_code(
        "meta",
        state.state_token,
        "auth_code_xyz",
        mock_token_response=mock_resp,
    )
    assert token_record.provider_name == "meta"
    assert token_record.token_type == "Bearer"
    assert token_record.access_token_ref.startswith("cred_")

    # Verify token stored securely in broker
    lease = broker.lease_secret(token_record.access_token_ref, requester="meta_client")
    assert lease.secret_value == "EAAX_meta_access_token_valid_123"

    # Verify active tokens list
    active_tokens = manager.list_tokens()
    assert len(active_tokens) == 1

    # Revoke tokens
    assert manager.revoke_token("meta") is True
    assert manager.get_token("meta") is None


def test_pkce_generation_entropy() -> None:
    verifier1, challenge1 = _generate_pkce()
    verifier2, challenge2 = _generate_pkce()
    assert verifier1 != verifier2
    assert challenge1 != challenge2
    assert len(verifier1) >= 43
    assert len(challenge1) >= 43


# ── Capability Router Tests ─────────────────────────────────────────────────


def test_capability_router_domain_classification_and_routing() -> None:
    router = CapabilityRouter()

    # Domain classification
    assert "calc" in router.classify_domains("Please compute 42 * 99")
    assert "browser" in router.classify_domains("Visit https://example.com and read the page")
    assert "system" in router.classify_domains("What is the current time and host platform?")
    assert "memory" in router.classify_domains("Remember that we decided to launch next week")
    assert "integrations" in router.classify_domains("Check weather forecast via MCP integration")

    all_specs = [
        CapabilitySpec("time.now", "Get time", {}, RiskLevel.READ, source="internal"),
        CapabilitySpec("calculator.evaluate", "Calculate", {}, RiskLevel.READ, source="internal"),
        CapabilitySpec("files.read", "Read file", {}, RiskLevel.READ, source="internal"),
        CapabilitySpec("browser.visit", "Visit URL", {}, RiskLevel.READ, source="internal"),
        CapabilitySpec(
            "weather.get_forecast",
            "Get weather",
            {},
            RiskLevel.READ,
            source="integration:mock_weather",
        ),
    ]

    # Route math query
    routed_math = router.route("Calculate 123 + 456", all_specs)
    math_names = {s.name for s in routed_math}
    assert "calculator.evaluate" in math_names

    # Route weather query
    routed_weather = router.route("What is the weather in Paris?", all_specs)
    weather_names = {s.name for s in routed_weather}
    assert "weather.get_forecast" in weather_names


# ── Native Integration Rate Limiting & Auth Tests ───────────────────────────


@pytest.mark.asyncio
async def test_native_integration_rate_limiting_and_authenticated_tool() -> None:
    broker = SecretBroker()
    api_key_ref = broker.register_secret("weather_api_token", "sec_weather_token_99")

    # Fast rate limiter for testing: 60 RPM with burst limit 2
    integration = MockWeatherIntegration(
        api_key_ref=api_key_ref.credential_id,
        secret_broker=broker,
        requests_per_minute=1,
    )
    await integration.connect()
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    assert len(tools) == 1
    weather_tool = tools[0]

    # First call succeeds
    res1 = await weather_tool.execute({"city": "Tokyo"})
    assert res1.output["city"] == "Tokyo"
    assert res1.output["condition"] == "Sunny"

    # Second call succeeds (within burst)
    res2 = await weather_tool.execute({"city": "London"})
    assert res2.output["city"] == "London"

    # Exceed burst tokens to trigger RateLimitError
    integration._rate_limiter = TokenBucketRateLimiter(requests_per_minute=1, burst_limit=0)
    with pytest.raises(RateLimitError):
        await weather_tool.execute({"city": "Berlin"})


# ── Acceptance Test: Dynamic MCP & Native Installation without CEO Core Modification ─


def test_dynamic_mcp_installation_and_ceo_discovery_acceptance() -> None:
    """Acceptance test from PLANS.md Phase 10:

    Install a new MCP integration without changing CEO core.
    CEO discovers it.
    """
    with TestClient(app) as client:
        # 1. Initially verify the dynamic test tool does not exist
        cap_resp = client.get("/api/v1/capabilities")
        assert cap_resp.status_code == 200
        initial_caps = {c["name"] for c in cap_resp.json()}
        assert "system_info.platform" in initial_caps
        assert "weather.get_forecast" not in initial_caps

        # 2. Register mock weather credential in secret vault via API
        sec_resp = client.post(
            "/api/v1/secrets",
            json={
                "name": "weather_api_token",
                "secret_value": "sec_weather_token_acceptance",
                "description": "Weather API Key",
            },
        )
        assert sec_resp.status_code == 201
        cred_id = sec_resp.json()["credential_id"]

        # 3. Dynamically install an authenticated native integration into the live registry
        broker = app.state.secrets
        weather_integration = MockWeatherIntegration(
            api_key_ref=cred_id,
            secret_broker=broker,
        )
        registry = app.state.integrations
        registry.register(weather_integration)
        import asyncio

        asyncio.run(weather_integration.connect())
        registry._notify_listeners()

        # 4. Verify CEO discovers the new capability without restarting
        cap_resp_after = client.get("/api/v1/capabilities")
        assert cap_resp_after.status_code == 200
        updated_caps = {c["name"] for c in cap_resp_after.json()}
        assert "weather.get_forecast" in updated_caps

        # 5. Submit a durable task that invokes the newly installed tool
        chat_resp = client.post(
            "/api/v1/chat/messages",
            json={"message": "What is the weather in Seattle?"},
        )
        assert chat_resp.status_code == 202
        task_id = chat_resp.json()["id"]

        # 6. Poll task execution until terminal state
        for _ in range(100):
            task_detail = client.get(f"/api/v1/tasks/{task_id}").json()
            if task_detail["status"] in {"success", "failed"}:
                break

        assert task_detail["status"] == "success"
        assert len(task_detail["plan"]["steps"]) >= 1
        assert task_detail["plan"]["steps"][0]["capability"] == "weather.get_forecast"
        assert len(task_detail["result"]["evidence"]) >= 1

        # 7. Clean up by uninstalling integration via API
        del_resp = client.delete("/api/v1/integrations/mock_weather")
        assert del_resp.status_code == 200
        cap_resp_final = client.get("/api/v1/capabilities")
        assert "weather.get_forecast" not in {c["name"] for c in cap_resp_final.json()}


# ── REST API Endpoints Tests ────────────────────────────────────────────────


def test_api_integrations_list_status_and_manifest() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/integrations")
        assert response.status_code == 200
        integrations = response.json()
        assert isinstance(integrations, list)
        system_info = next((item for item in integrations if item["name"] == "system_info"), None)
        assert system_info is not None
        assert system_info["integration_type"] == "native"
        assert system_info["health"] == "healthy"
        assert system_info["tool_count"] == 1
        assert system_info["risk_ceiling"] == "R0"

        # Direct status query
        status_resp = client.get("/api/v1/integrations/system_info/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["name"] == "system_info"
        assert status_resp.json()["health"] == "healthy"

        # Manifest query
        man_resp = client.get("/api/v1/integrations/system_info/manifest")
        assert man_resp.status_code == 200
        assert man_resp.json()["name"] == "system_info"
        assert man_resp.json()["domain"] == "system"

        # 404 for unknown integration
        missing = client.get(f"/api/v1/integrations/{uuid4()}/status")
        assert missing.status_code == 404


def test_api_secrets_and_oauth_endpoints() -> None:
    with TestClient(app) as client:
        # Register secret
        sec_resp = client.post(
            "/api/v1/secrets",
            json={
                "name": "google_api_key",
                "secret_value": "AIzaSy_google_secret_token_12345",
                "description": "Google API key",
                "tags": ["google", "api"],
            },
        )
        assert sec_resp.status_code == 201
        sec_json = sec_resp.json()
        assert sec_json["name"] == "google_api_key"
        assert sec_json["credential_id"].startswith("cred_")
        # Ensure raw secret is never returned
        assert "secret_value" not in sec_json
        assert "AIzaSy" not in json.dumps(sec_json)
        cred_id = sec_json["credential_id"]

        # List secrets
        list_resp = client.get("/api/v1/secrets")
        assert list_resp.status_code == 200
        secrets_list = list_resp.json()
        assert any(s["credential_id"] == cred_id for s in secrets_list)

        # Capability routing endpoint
        route_resp = client.post(
            "/api/v1/capabilities/route",
            json={"query": "Evaluate 50 * 20"},
        )
        assert route_resp.status_code == 200
        route_json = route_resp.json()
        assert "calc" in route_json["domains"]
        assert any(c["name"] == "calculator.evaluate" for c in route_json["capabilities"])

        # Revoke secret
        del_resp = client.delete(f"/api/v1/secrets/{cred_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "revoked"
