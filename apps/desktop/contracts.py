"""Contracts for standalone CEO OS Computer-Use Agent (CUA) Desktop App."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class CuaAppInfo:
    bundle_id: str
    name: str
    path: str
    running: bool
    frontmost: bool
    pid: int | None = None


@dataclass(frozen=True, slots=True)
class CuaDesktopState:
    running_apps_count: int
    frontmost_app: str
    accessibility_granted: bool
    screen_width: int = 1920
    screen_height: int = 1080
    captured_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True, slots=True)
class CuaActionRequest:
    action: str  # "focus_app", "type_text", "press_key", "list_apps", "screen_state"
    bundle_id: str | None = None
    text: str | None = None
    key: str | None = None
    modifiers: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CuaActionResult:
    action: str
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    executed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
