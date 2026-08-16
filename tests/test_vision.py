from __future__ import annotations

import asyncio
from typing import Any

import pytest

from vision.driver import DriverImage, DriverResult, VisionDriverError
from vision.runtime import VisionPolicy, VisionPolicyError, VisionRuntime, VisionStoppedError
from vision.tools import vision_tools


class FakeCuaDriver:
    def __init__(self) -> None:
        self.started = False
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.block = False
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.fail: VisionDriverError | None = None

    async def start(self) -> None:
        self.started = True

    async def shutdown(self) -> None:
        self.started = False

    async def status(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "available": self.started,
            "provider": "cua-driver",
            "driver_version": "test",
        }

    async def call(self, name: str, arguments: dict[str, Any]) -> DriverResult:
        self.calls.append((name, arguments))
        if self.block:
            self.entered.set()
            await self.release.wait()
        if self.fail is not None:
            raise self.fail
        if name == "list_windows":
            return DriverResult(
                {
                    "windows": [
                        {
                            "pid": 42,
                            "window_id": 7,
                            "app_name": "Fixture",
                            "title": "Canvas Success" if len(self.calls) > 2 else "Canvas",
                            "bounds": {"x": 0, "y": 0, "width": 800, "height": 600},
                            "is_on_screen": True,
                            "on_current_space": True,
                            "z_index": 1,
                            "secret_internal": "removed",
                        }
                    ]
                }
            )
        if name == "get_window_state":
            return DriverResult(
                {
                    "element_count": 0,
                    "snapshot_id": "s12345678",
                    "tree_markdown": "secret",
                    "screenshot_width": 800,
                    "screenshot_height": 600,
                    "window_bounds": {"width": 1600, "height": 1200},
                },
                (DriverImage("image/png", b"private screenshot pixels"),),
                degraded=True,
            )
        return DriverResult(
            {
                "effect": "confirmed",
                "route": "synthetic_events",
                "delivery": {"mode": "background"},
            },
            verified=True,
        )


async def ready_runtime(*, effects: bool = True) -> tuple[VisionRuntime, FakeCuaDriver]:
    driver = FakeCuaDriver()
    runtime = VisionRuntime(driver, VisionPolicy(effects, frozenset({"Fixture"})))
    await runtime.start()
    await runtime.list_windows()
    return runtime, driver


@pytest.mark.asyncio
async def test_capture_is_exactly_bound_and_never_exposes_image_bytes() -> None:
    runtime, driver = await ready_runtime()
    capture = await runtime.capture(session="canvas", pid=42, window_id=7)
    assert capture["snapshot_id"] == "s12345678"
    assert capture["degraded"] is True
    assert capture["trust"] == "untrusted_screen_content"
    assert capture["images"][0]["bytes"] == len(b"private screenshot pixels")
    assert len(capture["images"][0]["sha256"]) == 64
    assert b"private screenshot pixels" not in repr(capture).encode()
    assert driver.calls[-1] == (
        "get_window_state",
        {
            "session": "canvas",
            "pid": 42,
            "window_id": 7,
            "include_screenshot": True,
            "max_elements": 500,
            "max_depth": 20,
        },
    )
    with pytest.raises(VisionPolicyError, match="latest window listing"):
        await runtime.capture(session="canvas", pid=42, window_id=8)


@pytest.mark.asyncio
async def test_effects_require_policy_allowlist_and_are_bounded() -> None:
    disabled_driver = FakeCuaDriver()
    disabled = VisionRuntime(disabled_driver, VisionPolicy())
    await disabled.start()
    await disabled.list_windows()
    with pytest.raises(VisionPolicyError, match="disabled"):
        await disabled.effect(
            "click",
            {"session": "run", "pid": 42, "window_id": 7, "x": 10, "y": 20},
            idempotency_key="one",
        )

    runtime, driver = await ready_runtime()
    await runtime.capture(session="run", pid=42, window_id=7)
    result = await runtime.effect(
        "click",
        {
            "session": "run",
            "pid": 42,
            "window_id": 7,
            "x": 10,
            "y": 20,
            "expected_window_title": "Canvas Success",
        },
        idempotency_key="click-1",
    )
    assert result["verified"] is True and result["effect"] == "confirmed"
    assert result["driver_verified"] is True
    assert result["independently_verified"] is True
    click_call = next(arguments for name, arguments in driver.calls if name == "click")
    assert click_call == {
        "session": "run",
        "pid": 42,
        "window_id": 7,
        "delivery_mode": "background",
        "x": 20.0,
        "y": 40.0,
        "button": "left",
        "count": 1,
    }
    count = len(driver.calls)
    assert (
        await runtime.effect(
            "click",
            {
                "session": "run",
                "pid": 42,
                "window_id": 7,
                "x": 10,
                "y": 20,
                "expected_window_title": "Canvas Success",
            },
            idempotency_key="click-1",
        )
        == result
    )
    assert len(driver.calls) == count

    with pytest.raises(VisionPolicyError):
        await runtime.effect(
            "press_key",
            {"session": "run", "pid": 42, "window_id": 7, "key": "f13"},
            idempotency_key=None,
        )
    with pytest.raises(VisionPolicyError, match="Foreground"):
        await runtime.effect(
            "click",
            {
                "session": "run",
                "pid": 42,
                "window_id": 7,
                "x": 10,
                "y": 20,
                "delivery_mode": "foreground",
            },
            idempotency_key=None,
        )


@pytest.mark.asyncio
async def test_stop_cancels_active_driver_call_and_never_replays() -> None:
    runtime, driver = await ready_runtime()
    driver.block = True
    operation = asyncio.create_task(runtime.capture(session="cancel", pid=42, window_id=7))
    await asyncio.wait_for(driver.entered.wait(), timeout=1)
    stopped = await runtime.stop()
    with pytest.raises(VisionStoppedError):
        await operation
    assert stopped["state"]["stopped"] is True
    count = len(driver.calls)
    with pytest.raises(VisionStoppedError):
        await runtime.capture(session="cancel", pid=42, window_id=7)
    driver.release.set()
    await runtime.resume()
    assert len(driver.calls) == count


@pytest.mark.asyncio
async def test_driver_unknown_completion_is_propagated_without_retry() -> None:
    runtime, driver = await ready_runtime()
    await runtime.capture(session="run", pid=42, window_id=7)
    driver.fail = VisionDriverError("interrupted", "unknown", completion_unknown=True)
    with pytest.raises(VisionDriverError) as error:
        await runtime.effect(
            "click",
            {"session": "run", "pid": 42, "window_id": 7, "x": 1, "y": 1},
            idempotency_key="unknown",
        )
    assert error.value.completion_unknown is True
    assert len([name for name, _ in driver.calls if name == "click"]) == 1


@pytest.mark.asyncio
async def test_capabilities_hide_effects_by_default_and_mark_them_r2() -> None:
    runtime, _ = await ready_runtime()
    safe = vision_tools(runtime)
    names = {tool.spec.name for tool in safe}
    assert names == {"vision.status", "vision.windows.list", "vision.window.capture"}
    all_tools = vision_tools(runtime, include_effects=True)
    risks = {tool.spec.name: str(tool.spec.risk) for tool in all_tools}
    assert risks["vision.window.click"] == "R2"
    assert risks["vision.window.type"] == "R2"
