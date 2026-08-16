from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from apps.api.src.ceo_os_api.planner import DeterministicProvider
from computer.client import ComputerHelperError, MacHelperClient
from computer.controller import (
    ComputerController,
    ComputerPolicy,
    ComputerPolicyError,
    ComputerStoppedError,
)
from computer.tools import computer_tools


class FakeTransport:
    supported = True

    def __init__(self, frontmost: str | None = "com.apple.TextEdit") -> None:
        self.frontmost = frontmost
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.block = False

    async def request(self, action: str, **arguments: Any) -> dict[str, Any]:
        self.calls.append((action, arguments))
        if action == "status":
            return {"platform": "macos", "frontmost_bundle_id": self.frontmost}
        if self.block:
            self.started.set()
            await self.release.wait()
        if action in {"open_app", "focus_app"}:
            bundle_id = arguments["bundle_id"]
            self.frontmost = bundle_id
            return {
                "application": {
                    "bundle_id": bundle_id,
                    "running": True,
                    "frontmost": True,
                }
            }
        if action == "list_apps":
            return {"applications": []}
        return dict(arguments)


def allowed_controller(transport: FakeTransport) -> ComputerController:
    return ComputerController(
        transport,
        ComputerPolicy(True, frozenset({"com.apple.TextEdit"})),
    )


@pytest.mark.asyncio
async def test_effects_are_denied_by_default_and_bundle_allowlisted() -> None:
    transport = FakeTransport()
    disabled = ComputerController(transport, ComputerPolicy())
    with pytest.raises(ComputerPolicyError, match="disabled"):
        await disabled.execute("open_app", bundle_id="com.apple.TextEdit")

    enabled = allowed_controller(transport)
    with pytest.raises(ComputerPolicyError, match="allowlist"):
        await enabled.execute("open_app", bundle_id="com.example.Untrusted")


@pytest.mark.asyncio
async def test_input_requires_verified_frontmost_application() -> None:
    transport = FakeTransport(frontmost="com.apple.Safari")
    controller = allowed_controller(transport)
    with pytest.raises(ComputerPolicyError, match="frontmost"):
        await controller.execute("type_text", bundle_id="com.apple.TextEdit", text="harmless text")
    assert [action for action, _ in transport.calls] == ["status"]


@pytest.mark.asyncio
async def test_stop_invalidates_inflight_action_and_resume_does_not_replay() -> None:
    transport = FakeTransport()
    transport.block = True
    controller = allowed_controller(transport)
    action = asyncio.create_task(controller.execute("open_app", bundle_id="com.apple.TextEdit"))
    await asyncio.wait_for(transport.started.wait(), timeout=1)
    stopped_generation = controller.stop()["generation"]
    transport.release.set()
    with pytest.raises(ComputerStoppedError, match="invalidated"):
        await action
    assert len(transport.calls) == 1

    resumed = controller.resume()
    assert resumed["generation"] == stopped_generation + 1
    assert len(transport.calls) == 1


@pytest.mark.asyncio
async def test_tools_report_helper_evidence_and_hide_effects_by_default() -> None:
    transport = FakeTransport()
    controller = allowed_controller(transport)
    safe_tools = computer_tools(controller)
    assert {tool.spec.name for tool in safe_tools} == {
        "computer.status",
        "computer.apps.list",
    }
    all_tools = computer_tools(controller, include_effects=True)
    status = next(tool for tool in all_tools if tool.spec.name == "computer.status")
    result = await status.execute({})
    assert result.output["supported"] is True
    assert result.evidence == ["computer.status verified by macOS helper protocol V1"]


@pytest.mark.asyncio
async def test_planner_uses_typed_computer_capabilities_only_when_available() -> None:
    provider = DeterministicProvider()
    transport = FakeTransport()
    specs = [
        tool.spec for tool in computer_tools(allowed_controller(transport), include_effects=True)
    ]
    open_plan = await provider.plan("Open TextEdit", specs)
    assert open_plan.steps[0].capability == "computer.app.open"
    assert open_plan.steps[0].arguments == {"bundle_id": "com.apple.TextEdit"}

    type_plan = await provider.plan("Type Quarterly plan into TextEdit", specs)
    assert [step.capability for step in type_plan.steps] == [
        "computer.app.focus",
        "computer.text.type",
    ]
    unsupported = await provider.plan("Open TextEdit", [])
    assert unsupported.steps == []


def make_fake_helper(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "fake-helper"
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o100)
    return path


@pytest.mark.asyncio
async def test_client_rejects_protocol_mismatch_without_using_a_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = make_fake_helper(
        tmp_path,
        "import json,sys\nr=json.load(sys.stdin)\n"
        "print(json.dumps({'id': 'wrong', 'version': 1, 'ok': True, 'result': {}}))\n",
    )
    client = MacHelperClient(helper)
    monkeypatch.setattr("computer.client.sys.platform", "darwin")
    with pytest.raises(ComputerHelperError) as error:
        await client.request("status")
    assert error.value.code == "protocol_mismatch"


@pytest.mark.asyncio
async def test_client_accepts_matching_structured_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = make_fake_helper(
        tmp_path,
        "import json,sys\nr=json.load(sys.stdin)\n"
        "print(json.dumps({'id': r['id'], 'version': 1, 'ok': True, "
        "'result': {'platform': 'macos'}}))\n",
    )
    client = MacHelperClient(helper)
    monkeypatch.setattr("computer.client.sys.platform", "darwin")
    assert await client.request("status") == {"platform": "macos"}
