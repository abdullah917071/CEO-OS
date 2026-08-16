"""Tool permission governance and access level manager for Jarvis."""

from __future__ import annotations

from enum import StrEnum

from jarvis.backend.config.database import JarvisDatabase


class PermissionLevel(StrEnum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    DENY = "DENY"


# Default permission policies for safe execution
DEFAULT_TOOL_PERMISSIONS: dict[str, PermissionLevel] = {
    "open_application": PermissionLevel.ALLOW,
    "close_application": PermissionLevel.ALLOW,
    "focus_application": PermissionLevel.ALLOW,
    "set_volume": PermissionLevel.ALLOW,
    "get_volume": PermissionLevel.ALLOW,
    "mute": PermissionLevel.ALLOW,
    "unmute": PermissionLevel.ALLOW,
    "clipboard_read": PermissionLevel.ALLOW,
    "clipboard_write": PermissionLevel.ALLOW,
    "take_screenshot": PermissionLevel.ALLOW,
    "get_active_application": PermissionLevel.ALLOW,
    "get_active_window_title": PermissionLevel.ALLOW,
    "run_shortcut": PermissionLevel.ALLOW,
    "get_system_stats": PermissionLevel.ALLOW,
    "open_url": PermissionLevel.ALLOW,
    "search_google": PermissionLevel.ALLOW,
    "open_youtube": PermissionLevel.ALLOW,
    "play_pause_media": PermissionLevel.ALLOW,
    "next_track": PermissionLevel.ALLOW,
    "previous_track": PermissionLevel.ALLOW,
    "open_spotify": PermissionLevel.ALLOW,
    "execute_terminal_command": PermissionLevel.DENY,
}


class ToolPermissionManager:
    """Manages persistent ALLOW / ASK / DENY permission policies for all Jarvis tools."""

    def __init__(self, db: JarvisDatabase | None = None) -> None:
        self.db = db or JarvisDatabase()
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        stored = self.db.get_tool_permissions()
        for tool, lvl in DEFAULT_TOOL_PERMISSIONS.items():
            if tool not in stored:
                self.db.set_tool_permission(tool, lvl.value, f"Default permission for {tool}")

    def get_permission(self, tool_name: str) -> PermissionLevel:
        stored = self.db.get_tool_permissions()
        mode = stored.get(
            tool_name, DEFAULT_TOOL_PERMISSIONS.get(tool_name, PermissionLevel.ASK).value
        )
        try:
            return PermissionLevel(mode)
        except Exception:
            return PermissionLevel.ASK

    def set_permission(self, tool_name: str, level: PermissionLevel) -> None:
        self.db.set_tool_permission(tool_name, level.value)

    def list_permissions(self) -> dict[str, str]:
        stored = self.db.get_tool_permissions()
        result = {t: lvl.value for t, lvl in DEFAULT_TOOL_PERMISSIONS.items()}
        result.update(stored)
        return result
