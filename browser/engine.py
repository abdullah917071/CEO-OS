from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar, cast
from uuid import uuid4

from playwright.async_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    Route,
    async_playwright,
)
from playwright.async_api import (
    Error as PlaywrightError,
)

from browser.policy import ALLOWED_LOCATOR_KINDS, BrowserPolicy, BrowserPolicyError

T = TypeVar("T")
MAX_TEXT_CHARACTERS = 50_000
MAX_LOCATOR_VALUE = 2_000


class BrowserUnavailableError(RuntimeError):
    pass


class BrowserStoppedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LocatorSpec:
    kind: str
    value: str
    name: str | None = None
    exact: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> LocatorSpec:
        kind = str(value.get("kind", ""))
        target = str(value.get("value", ""))
        name = value.get("name")
        if kind not in ALLOWED_LOCATOR_KINDS:
            raise BrowserPolicyError("Unsupported locator kind")
        if not target or len(target) > MAX_LOCATOR_VALUE:
            raise BrowserPolicyError("Locator value is empty or too long")
        if target.lstrip().startswith(("//", "xpath=")):
            raise BrowserPolicyError("XPath locators are not allowed")
        if name is not None and (not isinstance(name, str) or len(name) > MAX_LOCATOR_VALUE):
            raise BrowserPolicyError("Locator name is invalid")
        if kind == "role" and not name:
            raise BrowserPolicyError("Role locators require an accessible name")
        return cls(kind, target, name, bool(value.get("exact", True)))


@dataclass(slots=True)
class BrowserSession:
    name: str
    context: BrowserContext
    persistent: bool
    pages: dict[str, Page] = field(default_factory=dict)


class PlaywrightBrowserEngine:
    def __init__(
        self,
        policy: BrowserPolicy,
        data_root: Path,
        *,
        headless: bool = True,
        enabled: bool = True,
        browsers_path: Path | None = None,
        timeout_ms: int = 10_000,
    ) -> None:
        self.policy = policy
        self.data_root = data_root
        self.headless = headless
        self.enabled = enabled
        self.browsers_path = browsers_path
        self.timeout_ms = timeout_ms
        self.sessions: dict[str, BrowserSession] = {}
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._startup_error: str | None = None
        self._stopped = False
        self._generation = 0
        self._operation_lock = asyncio.Lock()
        self._active_operation: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        if not self.enabled or self._browser is not None:
            return
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.data_root.chmod(0o700)
        self.policy.download_root.mkdir(parents=True, exist_ok=True)
        if self.browsers_path is not None:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(self.browsers_path.resolve())
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                downloads_path=str(self.policy.download_root.resolve()),
            )
            self._startup_error = None
        except PlaywrightError as exc:
            self._startup_error = str(exc)[:1_000]
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None

    async def shutdown(self) -> None:
        await self._close_all_sessions(persist=True)
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "available": self._browser is not None,
            "provider": "playwright-chromium",
            "headless": self.headless,
            "stopped": self._stopped,
            "generation": self._generation,
            "active_operation": self._active_operation is not None,
            "session_count": len(self.sessions),
            "allowed_origins": sorted(self.policy.allowed_origins),
            "effects_enabled": self.policy.effects_enabled,
            "persistent_profiles_enabled": self.policy.persistent_profiles_enabled,
            "startup_error": self._startup_error,
        }

    async def stop(self) -> dict[str, Any]:
        self._stopped = True
        self._generation += 1
        if self._active_operation is not None:
            self._active_operation.cancel()
            await asyncio.gather(self._active_operation, return_exceptions=True)
        await self._close_all_sessions()
        return self.status()

    def resume(self) -> dict[str, Any]:
        self._stopped = False
        self._generation += 1
        return self.status()

    async def open_session(self, name: str, *, persistent: bool = False) -> dict[str, Any]:
        self.policy.validate_session_name(name)
        self.policy.authorize_persistence(persistent)

        async def operation() -> dict[str, Any]:
            if name in self.sessions:
                raise ValueError(f"Browser session already exists: {name}")
            browser = self._require_browser()
            state_path = self._state_path(name)
            context = await browser.new_context(
                accept_downloads=True,
                storage_state=str(state_path) if persistent and state_path.is_file() else None,
            )
            context.set_default_timeout(self.timeout_ms)
            context.set_default_navigation_timeout(self.timeout_ms)
            await context.route("**/*", self._route_request)
            session = BrowserSession(name, context, persistent)
            self.sessions[name] = session
            context.on("page", lambda opened_page: self._on_page(session, opened_page))
            page = await context.new_page()
            page_id = self._register_page(session, page)
            return {"session": name, "persistent": persistent, "page_id": page_id}

        return await self._run(operation)

    async def close_session(self, name: str) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            session = self._session(name)
            if session.persistent:
                await self._save_storage_state(session)
            await session.context.close()
            del self.sessions[name]
            return {"session": name, "closed": True}

        return await self._run(operation)

    def list_sessions(self) -> dict[str, Any]:
        return {
            "sessions": [
                {"name": item.name, "persistent": item.persistent, "tabs": len(item.pages)}
                for item in self.sessions.values()
            ]
        }

    async def new_tab(self, session_name: str) -> dict[str, Any]:
        async def operation() -> dict[str, Any]:
            session = self._session(session_name)
            page = await session.context.new_page()
            return {"session": session_name, "page_id": self._register_page(session, page)}

        return await self._run(operation)

    def list_tabs(self, session_name: str) -> dict[str, Any]:
        session = self._session(session_name)
        return {
            "session": session_name,
            "tabs": [
                {"page_id": page_id, "url": page.url, "closed": page.is_closed()}
                for page_id, page in session.pages.items()
            ],
        }

    async def navigate(self, session_name: str, page_id: str, url: str) -> dict[str, Any]:
        self.policy.authorize_url(url)

        async def operation() -> dict[str, Any]:
            page = self._page(session_name, page_id)
            response = await page.goto(url, wait_until="domcontentloaded")
            self.policy.authorize_url(page.url)
            return {
                **await self._page_state(page, page_id),
                "status": response.status if response is not None else None,
            }

        return await self._run(operation)

    async def visit(
        self,
        session_name: str,
        url: str,
        *,
        max_characters: int = 20_000,
    ) -> dict[str, Any]:
        self.policy.validate_session_name(session_name)
        if session_name not in self.sessions:
            opened = await self.open_session(session_name)
            page_id = str(opened["page_id"])
        else:
            session = self._session(session_name)
            open_pages = [
                page_id for page_id, page in session.pages.items() if not page.is_closed()
            ]
            if open_pages:
                page_id = open_pages[0]
            else:
                page_id = str((await self.new_tab(session_name))["page_id"])
        navigation = await self.navigate(session_name, page_id, url)
        extraction = await self.extract(session_name, page_id, max_characters=max_characters)
        return {**extraction, "status": navigation["status"], "session": session_name}

    async def extract(
        self, session_name: str, page_id: str, *, max_characters: int = 20_000
    ) -> dict[str, Any]:
        if not 1 <= max_characters <= MAX_TEXT_CHARACTERS:
            raise BrowserPolicyError("Extraction limit must be between 1 and 50000")

        async def operation() -> dict[str, Any]:
            page = self._page(session_name, page_id)
            text = await page.locator("body").inner_text()
            links: list[dict[str, str]] = []
            page_links = await page.get_by_role("link").all()
            for link in page_links[:100]:
                links.append(
                    {
                        "text": (await link.inner_text())[:500],
                        "href": (await link.get_attribute("href") or "")[:2_000],
                    }
                )
            controls: list[dict[str, str]] = []
            page_controls = await page.locator("input, textarea, select").all()
            for control in page_controls[:100]:
                controls.append(
                    {
                        "tag": await control.evaluate("element => element.tagName.toLowerCase()"),
                        "type": (await control.get_attribute("type") or "")[:100],
                        "name": (await control.get_attribute("name") or "")[:500],
                        "id": (await control.get_attribute("id") or "")[:500],
                    }
                )
            return {
                **await self._page_state(page, page_id),
                "text": text[:max_characters],
                "truncated": len(text) > max_characters,
                "links": links,
                "controls": controls,
                "trust": "untrusted_page_content",
            }

        return await self._run(operation)

    async def click(
        self, session_name: str, page_id: str, locator_value: dict[str, Any]
    ) -> dict[str, Any]:
        self.policy.authorize_effect()
        locator_spec = LocatorSpec.from_dict(locator_value)

        async def operation() -> dict[str, Any]:
            page = self._page(session_name, page_id)
            locator = self._locator(page, locator_spec)
            await locator.click()
            await page.wait_for_load_state("domcontentloaded")
            return {
                **await self._page_state(page, page_id),
                "locator": self._safe_locator(locator_spec),
                "verified": True,
            }

        return await self._run(operation)

    async def fill(
        self, session_name: str, page_id: str, locator_value: dict[str, Any], value: str
    ) -> dict[str, Any]:
        self.policy.authorize_effect()
        if len(value) > 20_000:
            raise BrowserPolicyError("Fill value exceeds 20000 characters")
        locator_spec = LocatorSpec.from_dict(locator_value)

        async def operation() -> dict[str, Any]:
            locator = self._locator(self._page(session_name, page_id), locator_spec)
            await locator.fill(value)
            actual = await locator.input_value()
            if actual != value:
                raise RuntimeError("Browser fill postcondition failed")
            return {
                "session": session_name,
                "page_id": page_id,
                "locator": self._safe_locator(locator_spec),
                "value_length": len(value),
                "verified": True,
            }

        return await self._run(operation)

    async def upload(
        self, session_name: str, page_id: str, locator_value: dict[str, Any], path: str
    ) -> dict[str, Any]:
        self.policy.authorize_effect()
        source = self.policy.resolve_upload(path)
        locator_spec = LocatorSpec.from_dict(locator_value)

        async def operation() -> dict[str, Any]:
            locator = self._locator(self._page(session_name, page_id), locator_spec)
            await locator.set_input_files(source)
            return {
                "session": session_name,
                "page_id": page_id,
                "filename": source.name,
                "bytes": source.stat().st_size,
                "verified": True,
            }

        return await self._run(operation)

    async def download(
        self, session_name: str, page_id: str, locator_value: dict[str, Any]
    ) -> dict[str, Any]:
        self.policy.authorize_effect()
        locator_spec = LocatorSpec.from_dict(locator_value)

        async def operation() -> dict[str, Any]:
            page = self._page(session_name, page_id)
            async with page.expect_download() as download_info:
                await self._locator(page, locator_spec).click()
            download = await download_info.value
            destination = self.policy.resolve_download(download.suggested_filename)
            await download.save_as(destination)
            if not destination.is_file():
                raise RuntimeError("Browser download postcondition failed")
            return {
                "session": session_name,
                "page_id": page_id,
                "path": str(destination),
                "filename": destination.name,
                "bytes": destination.stat().st_size,
                "source_url": download.url,
                "verified": True,
            }

        return await self._run(operation)

    async def _run(self, operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
        if self._stopped:
            raise BrowserStoppedError("Browser automation is stopped")
        generation = self._generation
        async with self._operation_lock:
            if self._stopped or generation != self._generation:
                raise BrowserStoppedError("Browser operation was cancelled before execution")
            task: asyncio.Task[T] = asyncio.create_task(operation())
            self._active_operation = task
            try:
                result = await task
            except asyncio.CancelledError:
                if self._stopped or generation != self._generation:
                    raise BrowserStoppedError(
                        "Browser operation was invalidated by global stop"
                    ) from None
                raise
            finally:
                if self._active_operation is task:
                    self._active_operation = None
            if self._stopped or generation != self._generation:
                raise BrowserStoppedError("Browser operation was invalidated by global stop")
            return result

    async def _route_request(self, route: Route) -> None:
        try:
            self.policy.authorize_request_url(route.request.url)
        except BrowserPolicyError:
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    async def _close_all_sessions(self, *, persist: bool = False) -> None:
        sessions = list(self.sessions.values())
        self.sessions.clear()
        for session in sessions:
            if persist and session.persistent:
                await self._save_storage_state(session)
            await session.context.close()

    async def _save_storage_state(self, session: BrowserSession) -> None:
        state_path = self._state_path(session.name)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.parent.chmod(0o700)
        state_path.touch(mode=0o600, exist_ok=True)
        state_path.chmod(0o600)
        await session.context.storage_state(path=state_path)
        state_path.chmod(0o600)

    def _require_browser(self) -> Browser:
        if self._browser is None:
            raise BrowserUnavailableError(self._startup_error or "Chromium is unavailable")
        return self._browser

    def _session(self, name: str) -> BrowserSession:
        self.policy.validate_session_name(name)
        try:
            return self.sessions[name]
        except KeyError as exc:
            raise ValueError(f"Unknown browser session: {name}") from exc

    def _page(self, session_name: str, page_id: str) -> Page:
        session = self._session(session_name)
        try:
            page = session.pages[page_id]
        except KeyError as exc:
            raise ValueError(f"Unknown browser page: {page_id}") from exc
        if page.is_closed():
            raise ValueError(f"Browser page is closed: {page_id}")
        return page

    def _register_page(self, session: BrowserSession, page: Page) -> str:
        for page_id, existing in session.pages.items():
            if existing is page:
                return page_id
        page_id = str(uuid4())
        session.pages[page_id] = page
        return page_id

    def _on_page(self, session: BrowserSession, page: Page) -> None:
        self._register_page(session, page)

    def _state_path(self, session_name: str) -> Path:
        return self.data_root / "profiles" / f"{session_name}.json"

    async def _page_state(self, page: Page, page_id: str) -> dict[str, Any]:
        return {"page_id": page_id, "url": page.url, "title": await page.title()}

    @staticmethod
    def _safe_locator(value: LocatorSpec) -> dict[str, Any]:
        return {"kind": value.kind, "value": value.value, "name": value.name, "exact": value.exact}

    @staticmethod
    def _locator(page: Page, value: LocatorSpec) -> Locator:
        if value.kind == "role":
            return page.get_by_role(cast(Any, value.value), name=value.name, exact=value.exact)
        if value.kind == "label":
            return page.get_by_label(value.value, exact=value.exact)
        if value.kind == "placeholder":
            return page.get_by_placeholder(value.value, exact=value.exact)
        if value.kind == "text":
            return page.get_by_text(value.value, exact=value.exact)
        if value.kind == "test_id":
            return page.get_by_test_id(value.value)
        return page.locator(value.value)
