"""Universal tool registry and Gemini function declaration generator for Jarvis."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from jarvis.backend.tools import browser, macos, media
from jarvis.backend.tools.permissions import PermissionLevel, ToolPermissionManager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class JarvisToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[..., Awaitable[dict[str, Any]]]


class JarvisToolRegistry:
    """Universal tool registry mapping Gemini Live function declarations to local macOS handlers."""

    def __init__(self, permission_manager: ToolPermissionManager) -> None:
        self.permission_manager = permission_manager
        self._tools: dict[str, JarvisToolSpec] = {}
        self._register_default_tools()

    def register_tool(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        handler: Callable[..., Awaitable[dict[str, Any]]],
    ) -> None:
        """Register a custom or native tool."""
        self._tools[name] = JarvisToolSpec(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            handler=handler,
        )

    def has_tool(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools

    def get_tool(self, name: str) -> JarvisToolSpec | None:
        """Retrieve tool specification."""
        return self._tools.get(name)

    def list_tools(self) -> list[JarvisToolSpec]:
        """List all registered tool specifications."""
        return list(self._tools.values())

    def list_tool_names(self) -> list[str]:
        """List names of all registered tools."""
        return list(self._tools.keys())

    def _register_default_tools(self) -> None:
        """Populate initial macOS, browser, and media tools."""
        self.register_tool(
            name="open_application",
            description="Launch or focus a macOS application (e.g. Spotify, Safari, Chrome)",
            parameters_schema={
                "type": "OBJECT",
                "properties": {
                    "application": {
                        "type": "STRING",
                        "description": "The exact name of the application",
                    }
                },
                "required": ["application"],
            },
            handler=macos.open_application,
        )

        self.register_tool(
            name="close_application",
            description="Quit or close a running macOS application",
            parameters_schema={
                "type": "OBJECT",
                "properties": {
                    "application": {
                        "type": "STRING",
                        "description": "Name of the app to quit",
                    }
                },
                "required": ["application"],
            },
            handler=macos.close_application,
        )

        self.register_tool(
            name="set_volume",
            description="Set the macOS system speaker volume level from 0 to 100",
            parameters_schema={
                "type": "OBJECT",
                "properties": {
                    "level": {"type": "INTEGER", "description": "Volume percentage from 0 to 100"}
                },
                "required": ["level"],
            },
            handler=macos.set_volume,
        )

        self.register_tool(
            name="get_volume",
            description="Get current macOS system output volume percentage",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=macos.get_volume,
        )

        self.register_tool(
            name="mute",
            description="Mute system audio output",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=macos.mute,
        )

        self.register_tool(
            name="unmute",
            description="Unmute system audio output",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=macos.unmute,
        )

        self.register_tool(
            name="clipboard_read",
            description="Read the current text content from the macOS clipboard",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=macos.clipboard_read,
        )

        self.register_tool(
            name="clipboard_write",
            description="Write or copy text to the macOS clipboard",
            parameters_schema={
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING", "description": "Text to place on the clipboard"}
                },
                "required": ["text"],
            },
            handler=macos.clipboard_write,
        )

        self.register_tool(
            name="get_active_application",
            description="Get the name of the currently focused macOS application",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=macos.get_active_application,
        )

        self.register_tool(
            name="get_active_window_title",
            description="Get the window title of the currently focused application",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=macos.get_active_window_title,
        )

        self.register_tool(
            name="run_shortcut",
            description="Run an automated macOS Shortcut by name",
            parameters_schema={
                "type": "OBJECT",
                "properties": {
                    "shortcut_name": {
                        "type": "STRING",
                        "description": "Name of the macOS Shortcut",
                    }
                },
                "required": ["shortcut_name"],
            },
            handler=macos.run_shortcut,
        )

        self.register_tool(
            name="get_system_stats",
            description="Get platform, OS release, and battery information",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=macos.get_system_stats,
        )

        self.register_tool(
            name="open_url",
            description="Open a website URL in the default macOS web browser",
            parameters_schema={
                "type": "OBJECT",
                "properties": {
                    "url": {
                        "type": "STRING",
                        "description": "Web URL to open (e.g. 'https://news.ycombinator.com')",
                    }
                },
                "required": ["url"],
            },
            handler=browser.open_url,
        )

        self.register_tool(
            name="search_google",
            description="Search Google in the default browser",
            parameters_schema={
                "type": "OBJECT",
                "properties": {"query": {"type": "STRING", "description": "Search terms to query"}},
                "required": ["query"],
            },
            handler=browser.search_google,
        )

        self.register_tool(
            name="open_youtube",
            description="Open YouTube or search for videos",
            parameters_schema={
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Optional search term for YouTube"}
                },
            },
            handler=browser.open_youtube,
        )

        self.register_tool(
            name="open_spotify",
            description="Launch or bring Spotify to front",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=media.open_spotify,
        )

        self.register_tool(
            name="play_pause_media",
            description="Toggle play/pause on Spotify or Apple Music",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=media.play_pause_media,
        )

        self.register_tool(
            name="next_track",
            description="Skip to the next song or track on Spotify / Music",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=media.next_track,
        )

        self.register_tool(
            name="previous_track",
            description="Go back to the previous song on Spotify / Music",
            parameters_schema={"type": "OBJECT", "properties": {}},
            handler=media.previous_track,
        )

    def get_gemini_declarations(self) -> list[dict[str, Any]]:
        """Format enabled tools into Gemini Live function declarations."""
        declarations: list[dict[str, Any]] = []
        for name, spec in self._tools.items():
            perm = self.permission_manager.get_permission(name)
            if perm == PermissionLevel.DENY:
                continue  # Exclude denied tools from Gemini schema

            declarations.append(
                {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters_schema,
                }
            )
        return declarations

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with permission evaluation and error containment."""
        spec = self._tools.get(name)
        if not spec:
            return {"error": f"Tool '{name}' not found in registry", "status": "NOT_FOUND"}

        perm = self.permission_manager.get_permission(name)
        if perm == PermissionLevel.DENY:
            return {"error": f"Tool '{name}' is disabled by user policy", "status": "DENIED"}

        try:
            handler = spec.handler
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            return result
        except Exception as exc:
            logger.exception("Error executing tool '%s'", name)
            return {"status": "ERROR", "error": str(exc)}
