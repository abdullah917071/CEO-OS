from __future__ import annotations

from typing import Any, Protocol

from core.contracts import CapabilitySpec, RiskLevel, ToolResult


class BrowserRuntime(Protocol):
    def status(self) -> dict[str, Any]: ...
    def list_sessions(self) -> dict[str, Any]: ...
    def list_tabs(self, session_name: str) -> dict[str, Any]: ...
    async def open_session(self, name: str, *, persistent: bool = False) -> dict[str, Any]: ...
    async def close_session(self, name: str) -> dict[str, Any]: ...
    async def new_tab(self, session_name: str) -> dict[str, Any]: ...
    async def navigate(self, session_name: str, page_id: str, url: str) -> dict[str, Any]: ...
    async def visit(
        self, session_name: str, url: str, *, max_characters: int = 20_000
    ) -> dict[str, Any]: ...
    async def extract(
        self, session_name: str, page_id: str, *, max_characters: int = 20_000
    ) -> dict[str, Any]: ...
    async def click(
        self, session_name: str, page_id: str, locator_value: dict[str, Any]
    ) -> dict[str, Any]: ...
    async def fill(
        self, session_name: str, page_id: str, locator_value: dict[str, Any], value: str
    ) -> dict[str, Any]: ...
    async def upload(
        self,
        session_name: str,
        page_id: str,
        locator_value: dict[str, Any],
        path: str,
    ) -> dict[str, Any]: ...
    async def download(
        self, session_name: str, page_id: str, locator_value: dict[str, Any]
    ) -> dict[str, Any]: ...


LOCATOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["kind", "value"],
    "properties": {
        "kind": {
            "type": "string",
            "enum": ["role", "label", "placeholder", "text", "test_id", "css"],
        },
        "value": {"type": "string", "maxLength": 2_000},
        "name": {"type": "string", "maxLength": 2_000},
        "exact": {"type": "boolean"},
    },
}


class BrowserTool:
    def __init__(
        self,
        runtime: BrowserRuntime,
        name: str,
        description: str,
        operation: str,
        schema: dict[str, Any],
        risk: RiskLevel,
    ) -> None:
        self.runtime = runtime
        self.operation = operation
        self._spec = CapabilitySpec(name, description, schema, risk, source="playwright")
        self._idempotent_results: dict[str, ToolResult] = {}

    @property
    def spec(self) -> CapabilitySpec:
        return self._spec

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        if (
            idempotency_key
            and self.spec.risk != RiskLevel.READ
            and idempotency_key in self._idempotent_results
        ):
            return self._idempotent_results[idempotency_key]
        operation = self.operation
        if operation == "status":
            output = self.runtime.status()
        elif operation == "sessions_list":
            output = self.runtime.list_sessions()
        elif operation == "session_open":
            output = await self.runtime.open_session(
                str(arguments["session"]), persistent=bool(arguments.get("persistent", False))
            )
        elif operation == "session_close":
            output = await self.runtime.close_session(str(arguments["session"]))
        elif operation == "tab_open":
            output = await self.runtime.new_tab(str(arguments["session"]))
        elif operation == "tabs_list":
            output = self.runtime.list_tabs(str(arguments["session"]))
        elif operation == "navigate":
            output = await self.runtime.navigate(
                str(arguments["session"]), str(arguments["page_id"]), str(arguments["url"])
            )
        elif operation == "visit":
            output = await self.runtime.visit(
                str(arguments["session"]),
                str(arguments["url"]),
                max_characters=int(arguments.get("max_characters", 20_000)),
            )
        elif operation == "extract":
            output = await self.runtime.extract(
                str(arguments["session"]),
                str(arguments["page_id"]),
                max_characters=int(arguments.get("max_characters", 20_000)),
            )
        elif operation == "click":
            output = await self.runtime.click(
                str(arguments["session"]),
                str(arguments["page_id"]),
                dict(arguments["locator"]),
            )
        elif operation == "fill":
            output = await self.runtime.fill(
                str(arguments["session"]),
                str(arguments["page_id"]),
                dict(arguments["locator"]),
                str(arguments["value"]),
            )
        elif operation == "upload":
            output = await self.runtime.upload(
                str(arguments["session"]),
                str(arguments["page_id"]),
                dict(arguments["locator"]),
                str(arguments["path"]),
            )
        elif operation == "download":
            output = await self.runtime.download(
                str(arguments["session"]),
                str(arguments["page_id"]),
                dict(arguments["locator"]),
            )
        else:
            raise RuntimeError(f"Unsupported internal browser operation: {operation}")
        evidence = self._evidence(output)
        result = ToolResult(output, evidence)
        if idempotency_key and self.spec.risk != RiskLevel.READ:
            self._idempotent_results[idempotency_key] = result
        return result

    def _evidence(self, output: dict[str, Any]) -> list[str]:
        location = output.get("url") or output.get("path") or output.get("session")
        suffix = f": {location}" if location else ""
        return [f"{self.spec.name} verified by Playwright DOM state{suffix}"]


def browser_tools(runtime: BrowserRuntime, *, include_effects: bool = False) -> list[BrowserTool]:
    session_schema: dict[str, Any] = {
        "type": "object",
        "required": ["session"],
        "properties": {"session": {"type": "string", "maxLength": 64}},
    }
    page_schema: dict[str, Any] = {
        "type": "object",
        "required": ["session", "page_id"],
        "properties": {
            "session": {"type": "string", "maxLength": 64},
            "page_id": {"type": "string", "format": "uuid"},
        },
    }
    locator_schema: dict[str, Any] = {
        "type": "object",
        "required": ["session", "page_id", "locator"],
        "properties": {**page_schema["properties"], "locator": LOCATOR_SCHEMA},
    }
    safe = [
        BrowserTool(
            runtime,
            "browser.status",
            "Inspect browser runtime and policy",
            "status",
            {},
            RiskLevel.READ,
        ),
        BrowserTool(
            runtime,
            "browser.sessions.list",
            "List browser sessions without cookies",
            "sessions_list",
            {},
            RiskLevel.READ,
        ),
        BrowserTool(
            runtime,
            "browser.session.open",
            "Open an isolated named browser session",
            "session_open",
            {
                "type": "object",
                "required": ["session"],
                "properties": {
                    "session": {"type": "string", "maxLength": 64},
                    "persistent": {"type": "boolean"},
                },
            },
            RiskLevel.HARMLESS_WRITE,
        ),
        BrowserTool(
            runtime,
            "browser.session.close",
            "Close a named browser session",
            "session_close",
            session_schema,
            RiskLevel.HARMLESS_WRITE,
        ),
        BrowserTool(
            runtime,
            "browser.tab.open",
            "Open a tab in an isolated session",
            "tab_open",
            session_schema,
            RiskLevel.HARMLESS_WRITE,
        ),
        BrowserTool(
            runtime,
            "browser.tabs.list",
            "List tabs and URLs in a session",
            "tabs_list",
            session_schema,
            RiskLevel.READ,
        ),
        BrowserTool(
            runtime,
            "browser.navigate",
            "Navigate a tab to an allowlisted HTTP origin",
            "navigate",
            {
                "type": "object",
                "required": ["session", "page_id", "url"],
                "properties": {
                    **page_schema["properties"],
                    "url": {"type": "string", "maxLength": 8_000},
                },
            },
            RiskLevel.READ,
        ),
        BrowserTool(
            runtime,
            "browser.visit",
            "Open an allowlisted URL and return bounded untrusted DOM content",
            "visit",
            {
                "type": "object",
                "required": ["session", "url"],
                "properties": {
                    "session": {"type": "string", "maxLength": 64},
                    "url": {"type": "string", "maxLength": 8_000},
                    "max_characters": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50_000,
                    },
                },
            },
            RiskLevel.READ,
        ),
        BrowserTool(
            runtime,
            "browser.extract",
            "Extract bounded untrusted visible DOM content and links",
            "extract",
            {
                "type": "object",
                "required": ["session", "page_id"],
                "properties": {
                    **page_schema["properties"],
                    "max_characters": {"type": "integer", "minimum": 1, "maximum": 50_000},
                },
            },
            RiskLevel.READ,
        ),
    ]
    if not include_effects:
        return safe
    return [
        *safe,
        BrowserTool(
            runtime,
            "browser.click",
            "Click one strict DOM locator",
            "click",
            locator_schema,
            RiskLevel.EXTERNAL_COMMUNICATION,
        ),
        BrowserTool(
            runtime,
            "browser.fill",
            "Fill one strict DOM form control",
            "fill",
            {
                "type": "object",
                "required": ["session", "page_id", "locator", "value"],
                "properties": {
                    **locator_schema["properties"],
                    "value": {"type": "string", "maxLength": 20_000},
                },
            },
            RiskLevel.EXTERNAL_COMMUNICATION,
        ),
        BrowserTool(
            runtime,
            "browser.upload",
            "Upload one workspace-scoped file through a strict DOM locator",
            "upload",
            {
                "type": "object",
                "required": ["session", "page_id", "locator", "path"],
                "properties": {
                    **locator_schema["properties"],
                    "path": {"type": "string", "maxLength": 4_000},
                },
            },
            RiskLevel.EXTERNAL_COMMUNICATION,
        ),
        BrowserTool(
            runtime,
            "browser.download",
            "Download through a strict DOM locator into the workspace",
            "download",
            locator_schema,
            RiskLevel.HARMLESS_WRITE,
        ),
    ]
