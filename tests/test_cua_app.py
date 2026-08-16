"""Unit and integration tests for CEO OS Standalone CUA Desktop App and endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.ceo_os_api.main import app
from apps.desktop.contracts import CuaAppInfo, CuaDesktopState
from apps.desktop.cua_app import CuaDesktopApp


@pytest.mark.asyncio
async def test_cua_desktop_app_methods() -> None:
    desktop_app = CuaDesktopApp(effects_enabled=False)

    # 1. List applications
    apps = await desktop_app.list_applications()
    assert isinstance(apps, list)
    if apps:
        assert isinstance(apps[0], CuaAppInfo)

    # 2. Desktop State
    state = await desktop_app.get_desktop_state()
    assert isinstance(state, CuaDesktopState)
    assert state.accessibility_granted is True

    # 3. Direct Actions (simulated with effects_enabled=False)
    focus_res = await desktop_app.focus_application("Finder")
    assert focus_res.action == "focus_app"

    type_res = await desktop_app.type_text("Hello CEO OS")
    assert type_res.action == "type_text"

    key_res = await desktop_app.press_key("return")
    assert key_res.action == "press_key"


@pytest.mark.asyncio
async def test_cua_api_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Status
        res = await client.get("/api/v1/cua/status")
        assert res.status_code == 200
        data = res.json()
        assert data["enabled"] is True
        assert "frontmost_app" in data

        # 2. Apps
        res = await client.get("/api/v1/cua/apps")
        assert res.status_code == 200
        apps_data = res.json()
        assert "count" in apps_data
        assert isinstance(apps_data["apps"], list)

        # 3. Action: Focus
        res = await client.post(
            "/api/v1/cua/action",
            json={"action": "focus_app", "bundle_id": "com.apple.finder"},
        )
        assert res.status_code == 200
        action_data = res.json()
        assert action_data["action"] == "focus_app"

        # 4. Action: Type Text
        res = await client.post(
            "/api/v1/cua/action",
            json={"action": "type_text", "text": "test typing"},
        )
        assert res.status_code == 200
        type_data = res.json()
        assert type_data["action"] == "type_text"

        # 5. Execute Directive
        res = await client.post(
            "/api/v1/cua/execute",
            json={"objective": "Inspect running applications and verify system state"},
        )
        assert res.status_code == 200
        exec_data = res.json()
        assert "status" in exec_data
        assert "final_answer" in exec_data
