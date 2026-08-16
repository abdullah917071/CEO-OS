from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any

from computer.client import ComputerHelperError, ComputerTransport

EFFECT_ACTIONS = {"open_app", "focus_app", "type_text", "key_press"}


class ComputerPolicyError(PermissionError):
    pass


class ComputerStoppedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ComputerPolicy:
    effects_enabled: bool = False
    allowed_bundle_ids: frozenset[str] = frozenset()

    def authorize(self, action: str, bundle_id: str | None) -> None:
        if action not in EFFECT_ACTIONS:
            return
        if not self.effects_enabled:
            raise ComputerPolicyError("Computer effects are disabled")
        if bundle_id is None or bundle_id not in self.allowed_bundle_ids:
            raise ComputerPolicyError("Application is not in the computer-control allowlist")


@dataclass(slots=True)
class ComputerState:
    stopped: bool = False
    generation: int = 0
    active_action: str | None = None
    active_bundle_id: str | None = None
    frontmost_bundle_id: str | None = None


class ComputerController:
    def __init__(self, transport: ComputerTransport, policy: ComputerPolicy) -> None:
        self.transport = transport
        self.policy = policy
        self.state = ComputerState()
        self._input_lock = asyncio.Lock()
        self._active_request: asyncio.Task[dict[str, Any]] | None = None

    async def status(self) -> dict[str, Any]:
        helper: dict[str, Any] = {
            "platform": "unsupported",
            "accessibility_trusted": False,
        }
        if self.transport.supported:
            helper = await self.transport.request("status")
            self.state.frontmost_bundle_id = helper.get("frontmost_bundle_id")
        return {
            **helper,
            "supported": self.transport.supported,
            "policy": {
                "effects_enabled": self.policy.effects_enabled,
                "allowed_bundle_ids": sorted(self.policy.allowed_bundle_ids),
            },
            "state": asdict(self.state),
        }

    def stop(self) -> dict[str, Any]:
        self.state.stopped = True
        self.state.generation += 1
        self.state.active_action = None
        self.state.active_bundle_id = None
        if self._active_request is not None:
            self._active_request.cancel()
        return asdict(self.state)

    def resume(self) -> dict[str, Any]:
        self.state.stopped = False
        self.state.generation += 1
        return asdict(self.state)

    async def execute(
        self, action: str, *, bundle_id: str | None = None, **arguments: Any
    ) -> dict[str, Any]:
        if not self.transport.supported:
            raise ComputerHelperError("unsupported_environment", "macOS helper is unavailable")
        self.policy.authorize(action, bundle_id)
        if self.state.stopped:
            raise ComputerStoppedError("Computer control is stopped")
        generation = self.state.generation
        async with self._input_lock:
            if self.state.stopped or generation != self.state.generation:
                raise ComputerStoppedError("Computer action was cancelled before execution")
            if action in {"type_text", "key_press"}:
                status = await self.transport.request("status")
                frontmost = status.get("frontmost_bundle_id")
                self.state.frontmost_bundle_id = frontmost
                if frontmost != bundle_id:
                    raise ComputerPolicyError(
                        "Input target is not the verified frontmost application"
                    )
                if self.state.stopped or generation != self.state.generation:
                    raise ComputerStoppedError("Computer action was cancelled before input")
            self.state.active_action = action
            self.state.active_bundle_id = bundle_id
            request = asyncio.create_task(
                self.transport.request(
                    action, **({"bundle_id": bundle_id} if bundle_id else {}), **arguments
                )
            )
            self._active_request = request
            try:
                result = await request
            except asyncio.CancelledError:
                if self.state.stopped or generation != self.state.generation:
                    raise ComputerStoppedError(
                        "Computer action was invalidated by global stop"
                    ) from None
                raise
            finally:
                if self._active_request is request:
                    self._active_request = None
                self.state.active_action = None
                self.state.active_bundle_id = None
            if self.state.stopped or generation != self.state.generation:
                raise ComputerStoppedError("Computer action was invalidated by global stop")
            application = result.get("application")
            if isinstance(application, dict) and application.get("frontmost"):
                self.state.frontmost_bundle_id = application.get("bundle_id")
            return result
