"""Standalone CEO OS Computer-Use Agent (CUA) Desktop Host Controller package."""

from __future__ import annotations

from apps.desktop.contracts import CuaActionRequest, CuaActionResult, CuaAppInfo, CuaDesktopState
from apps.desktop.cua_app import CuaDesktopApp

__all__ = [
    "CuaActionRequest",
    "CuaActionResult",
    "CuaAppInfo",
    "CuaDesktopApp",
    "CuaDesktopState",
]
