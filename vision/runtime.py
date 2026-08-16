from __future__ import annotations

import asyncio
import re
from dataclasses import asdict, dataclass
from typing import Any, TypeVar

from vision.driver import DriverResult, VisionDriver, VisionDriverError, public_image_evidence

T = TypeVar("T")
SESSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
ALLOWED_KEYS = {"return", "tab", "escape", "up", "down", "left", "right", "space", "delete"}
ALLOWED_MODIFIERS = {"cmd", "shift", "option", "alt", "ctrl", "fn"}


class VisionPolicyError(PermissionError):
    pass


class VisionStoppedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VisionPolicy:
    effects_enabled: bool = False
    allowed_app_names: frozenset[str] = frozenset()
    foreground_escalation_enabled: bool = False
    max_text_bytes: int = 10_000


@dataclass(slots=True)
class VisionState:
    stopped: bool = False
    generation: int = 0
    active_action: str | None = None


class VisionRuntime:
    def __init__(self, driver: VisionDriver, policy: VisionPolicy) -> None:
        self.driver = driver
        self.policy = policy
        self.state = VisionState()
        self._operation_lock = asyncio.Lock()
        self._active: asyncio.Task[Any] | None = None
        self._window_owners: dict[tuple[int, int], str] = {}
        self._capture_frames: dict[tuple[int, int], tuple[float, float]] = {}
        self._effect_cache: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        await self.driver.start()

    async def shutdown(self) -> None:
        await self.stop()
        await self.driver.shutdown()

    async def status(self) -> dict[str, Any]:
        return {
            **await self.driver.status(),
            "policy": {
                "effects_enabled": self.policy.effects_enabled,
                "allowed_app_names": sorted(self.policy.allowed_app_names),
                "capture_scope": "window",
                "foreground_escalation_enabled": self.policy.foreground_escalation_enabled,
            },
            "state": asdict(self.state),
        }

    async def stop(self) -> dict[str, Any]:
        self.state.stopped = True
        self.state.generation += 1
        self.state.active_action = None
        if self._active is not None:
            self._active.cancel()
            await asyncio.gather(self._active, return_exceptions=True)
        return await self.status()

    async def resume(self) -> dict[str, Any]:
        self.state.stopped = False
        self.state.generation += 1
        return await self.status()

    async def list_windows(self, *, on_screen_only: bool = True) -> dict[str, Any]:
        result = await self._run("list_windows", {"on_screen_only": on_screen_only})
        windows = result.structured.get("windows", [])
        safe_windows: list[dict[str, Any]] = []
        self._window_owners.clear()
        if isinstance(windows, list):
            for value in windows[:500]:
                if not isinstance(value, dict):
                    continue
                pid, window_id = value.get("pid"), value.get("window_id")
                app_name = value.get("app_name")
                if (
                    isinstance(pid, int)
                    and isinstance(window_id, int)
                    and isinstance(app_name, str)
                ):
                    self._window_owners[(pid, window_id)] = app_name
                    safe_windows.append(
                        {
                            key: value.get(key)
                            for key in (
                                "pid",
                                "window_id",
                                "app_name",
                                "title",
                                "bounds",
                                "is_on_screen",
                                "on_current_space",
                                "z_index",
                            )
                        }
                    )
        return {"windows": safe_windows, "count": len(safe_windows)}

    async def capture(self, *, session: str, pid: int, window_id: int) -> dict[str, Any]:
        self._validate_target(session, pid, window_id, effect=False)
        result = await self._run(
            "get_window_state",
            {
                "session": session,
                "pid": pid,
                "window_id": window_id,
                "include_screenshot": True,
                "max_elements": 500,
                "max_depth": 20,
            },
        )
        screenshot_width = result.structured.get("screenshot_width")
        screenshot_height = result.structured.get("screenshot_height")
        window_bounds = result.structured.get("window_bounds")
        if (
            isinstance(screenshot_width, (int, float))
            and screenshot_width > 0
            and isinstance(screenshot_height, (int, float))
            and screenshot_height > 0
            and isinstance(window_bounds, dict)
            and isinstance(window_bounds.get("width"), (int, float))
            and isinstance(window_bounds.get("height"), (int, float))
        ):
            self._capture_frames[(pid, window_id)] = (
                float(window_bounds["width"]) / float(screenshot_width),
                float(window_bounds["height"]) / float(screenshot_height),
            )
        return {
            "pid": pid,
            "window_id": window_id,
            "session": session,
            "images": public_image_evidence(result.images),
            "element_count": result.structured.get("element_count"),
            "snapshot_id": result.structured.get("snapshot_id"),
            "screenshot_width": screenshot_width,
            "screenshot_height": screenshot_height,
            "degraded": result.degraded,
            "trust": "untrusted_screen_content",
        }

    async def effect(
        self,
        action: str,
        arguments: dict[str, Any],
        *,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if action not in {"click", "type_text", "press_key", "scroll"}:
            raise VisionPolicyError("Unsupported visual action")
        session = str(arguments.get("session", ""))
        pid, window_id = arguments.get("pid"), arguments.get("window_id")
        if not isinstance(pid, int) or not isinstance(window_id, int):
            raise VisionPolicyError("Visual actions require exact pid and window_id")
        self._validate_target(session, pid, window_id, effect=True)
        if idempotency_key and idempotency_key in self._effect_cache:
            return self._effect_cache[idempotency_key]
        payload = self._validate_effect_arguments(action, arguments)
        result = await self._run(action, payload)
        expected_title = arguments.get("expected_window_title")
        independently_verified = False
        if expected_title is not None:
            if not isinstance(expected_title, str) or not 1 <= len(expected_title) <= 500:
                raise VisionPolicyError("Expected window title is invalid")
            independently_verified = await self._wait_for_window_title(
                pid, window_id, expected_title
            )
            if not independently_verified:
                raise RuntimeError("Independent visual action postcondition failed")
        output = {
            "action": action,
            "pid": pid,
            "window_id": window_id,
            "session": session,
            "effect": result.structured.get("effect", "unverifiable"),
            "route": result.structured.get("route"),
            "delivery": result.structured.get("delivery"),
            "driver_verified": result.verified,
            "independently_verified": independently_verified,
            "verified": result.verified or independently_verified,
            "degraded": result.degraded,
        }
        if idempotency_key:
            self._effect_cache[idempotency_key] = output
        return output

    async def _wait_for_window_title(self, pid: int, window_id: int, expected_title: str) -> bool:
        for _ in range(50):
            listed = await self._run("list_windows", {"on_screen_only": False})
            windows = listed.structured.get("windows", [])
            if isinstance(windows, list) and any(
                isinstance(window, dict)
                and window.get("pid") == pid
                and window.get("window_id") == window_id
                and window.get("title") == expected_title
                for window in windows
            ):
                return True
            await asyncio.sleep(0.1)
        return False

    def _validate_target(self, session: str, pid: int, window_id: int, *, effect: bool) -> None:
        if not SESSION_PATTERN.fullmatch(session):
            raise VisionPolicyError("Vision session name is invalid")
        if pid <= 0 or window_id <= 0:
            raise VisionPolicyError("Vision target identifiers must be positive")
        app_name = self._window_owners.get((pid, window_id))
        if app_name is None:
            raise VisionPolicyError("Target must come from the latest window listing")
        if effect:
            if not self.policy.effects_enabled:
                raise VisionPolicyError("Vision effects are disabled")
            if app_name not in self.policy.allowed_app_names:
                raise VisionPolicyError("Target application is not allowlisted")

    def _validate_effect_arguments(self, action: str, value: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "session": value["session"],
            "pid": value["pid"],
            "window_id": value["window_id"],
        }
        delivery_mode = value.get("delivery_mode", "background")
        if delivery_mode not in {"background", "foreground"}:
            raise VisionPolicyError("Visual delivery mode is invalid")
        if delivery_mode == "foreground" and not self.policy.foreground_escalation_enabled:
            raise VisionPolicyError("Foreground visual delivery is disabled")
        payload["delivery_mode"] = delivery_mode
        if action == "click":
            x, y = value.get("x"), value.get("y")
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise VisionPolicyError("Visual click requires numeric x and y")
            if not (0 <= x <= 16_384 and 0 <= y <= 16_384):
                raise VisionPolicyError("Visual click coordinates are outside supported bounds")
            x, y = self._map_screenshot_point(value["pid"], value["window_id"], x, y)
            payload.update({"x": x, "y": y, "button": "left", "count": 1})
        elif action == "type_text":
            text = value.get("text")
            if not isinstance(text, str) or len(text.encode()) > self.policy.max_text_bytes:
                raise VisionPolicyError("Visual text is invalid or too long")
            payload["text"] = text
            if isinstance(value.get("x"), (int, float)) and isinstance(
                value.get("y"), (int, float)
            ):
                x, y = self._map_screenshot_point(
                    value["pid"], value["window_id"], value["x"], value["y"]
                )
                payload.update({"x": x, "y": y})
        elif action == "press_key":
            key = value.get("key")
            modifiers = value.get("modifiers", [])
            if key not in ALLOWED_KEYS or not isinstance(modifiers, list):
                raise VisionPolicyError("Visual key is not allowlisted")
            if any(item not in ALLOWED_MODIFIERS for item in modifiers):
                raise VisionPolicyError("Visual key modifier is not allowlisted")
            payload.update({"key": key, "modifiers": modifiers})
        else:
            direction, amount = value.get("direction"), value.get("amount", 3)
            if direction not in {"up", "down", "left", "right"}:
                raise VisionPolicyError("Visual scroll direction is invalid")
            if not isinstance(amount, int) or not 1 <= amount <= 20:
                raise VisionPolicyError("Visual scroll amount is invalid")
            payload.update({"direction": direction, "amount": amount, "by": "line"})
        return payload

    def _map_screenshot_point(
        self, pid: int, window_id: int, x: float, y: float
    ) -> tuple[float, float]:
        try:
            x_scale, y_scale = self._capture_frames[(pid, window_id)]
        except KeyError as exc:
            raise VisionPolicyError(
                "A current window capture is required before pixel actions"
            ) from exc
        return round(x * x_scale, 3), round(y * y_scale, 3)

    async def _run(self, action: str, arguments: dict[str, Any]) -> DriverResult:
        if self.state.stopped:
            raise VisionStoppedError("Vision control is stopped")
        generation = self.state.generation
        async with self._operation_lock:
            if self.state.stopped or generation != self.state.generation:
                raise VisionStoppedError("Vision operation was cancelled before execution")
            self.state.active_action = action
            task = asyncio.create_task(self.driver.call(action, arguments))
            self._active = task
            try:
                result = await task
            except asyncio.CancelledError:
                if self.state.stopped or generation != self.state.generation:
                    raise VisionStoppedError(
                        "Vision operation was invalidated by global stop"
                    ) from None
                raise
            except VisionDriverError:
                raise
            finally:
                if self._active is task:
                    self._active = None
                self.state.active_action = None
            if self.state.stopped or generation != self.state.generation:
                raise VisionStoppedError("Vision operation was invalidated by global stop")
            return result
