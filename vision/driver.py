from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol


class VisionDriverError(RuntimeError):
    def __init__(self, code: str, message: str, *, completion_unknown: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.completion_unknown = completion_unknown


@dataclass(frozen=True, slots=True)
class DriverImage:
    mime_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class DriverResult:
    structured: dict[str, Any]
    images: tuple[DriverImage, ...] = ()
    verified: bool = False
    degraded: bool = False


class VisionDriver(Protocol):
    async def start(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def status(self) -> dict[str, Any]: ...

    async def call(self, name: str, arguments: dict[str, Any]) -> DriverResult: ...


class CuaSdkDriver:
    """Narrow adapter around Cua Driver's in-process typed runtime."""

    allowed_tools = {
        "list_windows",
        "get_window_state",
        "click",
        "type_text",
        "press_key",
        "scroll",
    }

    def __init__(self, *, enabled: bool) -> None:
        self.enabled = enabled
        self._driver: Any | None = None
        self._startup_error: str | None = None

    async def start(self) -> None:
        if not self.enabled or self._driver is not None:
            return
        try:
            from cua_driver import CuaDriver  # type: ignore[import-untyped]

            self._driver = CuaDriver.create()
            if not self._driver.is_available():
                await self._driver.shutdown()
                self._driver = None
                self._startup_error = "Cua Driver runtime is unavailable"
        except BaseException as exc:
            self._driver = None
            self._startup_error = f"{type(exc).__name__}: {exc}"[:1_000]

    async def shutdown(self) -> None:
        driver, self._driver = self._driver, None
        if driver is not None:
            await driver.shutdown()

    async def status(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "enabled": self.enabled,
            "available": self._driver is not None,
            "provider": "cua-driver",
            "startup_error": self._startup_error,
        }
        if self._driver is not None:
            metadata = await self._driver.metadata()
            mode = self._driver.execution_mode()
            result.update(
                {
                    "driver_version": metadata.driver_version,
                    "contract_version": metadata.contract_version,
                    "execution_mode": str(mode),
                    "embedded": metadata.embedded,
                }
            )
        return result

    async def call(self, name: str, arguments: dict[str, Any]) -> DriverResult:
        if name not in self.allowed_tools:
            raise VisionDriverError("tool_not_allowed", "Cua Driver tool is not exposed")
        if self._driver is None:
            raise VisionDriverError(
                "driver_unavailable", self._startup_error or "Cua Driver is unavailable"
            )
        try:
            raw = await self._driver.call_tool(name, json.dumps(arguments, separators=(",", ":")))
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            completion_unknown = "ActionInterrupted" in type(exc).__name__
            raise VisionDriverError(
                "driver_call_failed", str(exc)[:500], completion_unknown=completion_unknown
            ) from exc
        if raw.is_error:
            raise VisionDriverError(raw.error_code or "driver_tool_error", raw.text[:500])
        structured: dict[str, Any] = {}
        if raw.structured_json:
            decoded = json.loads(raw.structured_json)
            if isinstance(decoded, dict):
                structured = decoded
        images = tuple(
            DriverImage(str(image.mime_type), base64.b64decode(image.data_base64, validate=True))
            for image in raw.images
        )
        verified = bool(raw.verification and raw.verification.stable) or bool(
            raw.action and str(raw.action.effect).lower().endswith("confirmed")
        )
        return DriverResult(structured, images, verified, bool(raw.degraded))


def public_image_evidence(images: tuple[DriverImage, ...]) -> list[dict[str, Any]]:
    return [
        {
            "mime_type": image.mime_type,
            "bytes": len(image.data),
            "sha256": hashlib.sha256(image.data).hexdigest(),
        }
        for image in images
    ]
