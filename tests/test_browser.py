from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from playwright.async_api import Error as PlaywrightError

from apps.api.src.ceo_os_api.planner import DeterministicProvider
from browser.engine import (
    BrowserStoppedError,
    LocatorSpec,
    PlaywrightBrowserEngine,
)
from browser.policy import BrowserPolicy, BrowserPolicyError, normalized_origin
from browser.tools import browser_tools


class FixtureServer:
    def __init__(self) -> None:
        self.server: asyncio.Server | None = None
        self.origin = ""
        self.external_origin = ""
        self.requests: list[str] = []
        self.slow_started = asyncio.Event()
        self.slow_release = asyncio.Event()

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        socket = self.server.sockets[0]
        self.origin = f"http://127.0.0.1:{socket.getsockname()[1]}"

    async def close(self) -> None:
        self.slow_release.set()
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=2)
            lines = raw.decode(errors="replace").split("\r\n")
            path = lines[0].split(" ")[1]
            headers = {
                key.lower(): value.strip()
                for line in lines[1:]
                if ":" in line
                for key, value in [line.split(":", 1)]
            }
            self.requests.append(path)
            status = "200 OK"
            response_headers = {"Content-Type": "text/html; charset=utf-8"}
            if path == "/":
                body = f"""<!doctype html><html><head><title>CEO Fixture</title></head>
                <body><h1>Fixture Home</h1><p>{"bounded " * 100}</p>
                <label>Name <input id="name"></label>
                <label>Upload <input id="upload" type="file"></label>
                <button onclick="document.querySelector('h1').textContent='Clicked'">
                  Change heading
                </button>
                <button>Duplicate</button><button>Duplicate</button>
                <button onclick="window.open('/popup', '_blank')">Open popup</button>
                <a href="/second">Second page</a><a href="/download">Download report</a>
                <img src="{self.external_origin}/pixel" alt="blocked external resource">
                </body></html>"""
            elif path == "/second":
                body = "<html><head><title>Second</title></head><body>Second page</body></html>"
            elif path == "/popup":
                body = "<html><head><title>Popup</title></head><body>Popup page</body></html>"
            elif path == "/set-cookie":
                response_headers["Set-Cookie"] = "fixture_session=alpha; Path=/; HttpOnly"
                body = "<html><body>Cookie set</body></html>"
            elif path == "/cookie":
                body = f"<html><body>Cookie: {headers.get('cookie', 'none')}</body></html>"
            elif path == "/download":
                response_headers = {
                    "Content-Type": "text/plain",
                    "Content-Disposition": 'attachment; filename="fixture-report.txt"',
                }
                body = "verified browser download"
            elif path == "/redirect-external":
                status = "302 Found"
                response_headers["Location"] = f"{self.external_origin}/blocked"
                body = "redirect"
            elif path == "/slow":
                self.slow_started.set()
                await self.slow_release.wait()
                body = "<html><body>Slow response complete</body></html>"
            else:
                status = "404 Not Found"
                body = "not found"
            encoded = body.encode()
            response_headers["Content-Length"] = str(len(encoded))
            header_text = "".join(f"{key}: {value}\r\n" for key, value in response_headers.items())
            writer.write(f"HTTP/1.1 {status}\r\n{header_text}Connection: close\r\n\r\n".encode())
            writer.write(encoded)
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, TimeoutError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()


def make_engine(
    tmp_path: Path,
    origins: set[str],
    *,
    effects: bool = True,
    persistence: bool = True,
) -> PlaywrightBrowserEngine:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    policy = BrowserPolicy(
        frozenset(origins),
        workspace,
        workspace / "downloads",
        effects_enabled=effects,
        persistent_profiles_enabled=persistence,
    )
    return PlaywrightBrowserEngine(
        policy,
        workspace / ".ceo-os/browser",
        browsers_path=Path(".playwright-browsers"),
        timeout_ms=3_000,
    )


@pytest.mark.asyncio
async def test_real_chromium_dom_fixture_acceptance(tmp_path: Path) -> None:
    fixture, external = FixtureServer(), FixtureServer()
    await fixture.start()
    await external.start()
    fixture.external_origin = external.origin
    engine = make_engine(tmp_path, {fixture.origin})
    await engine.start()
    assert engine.status()["available"] is True
    try:
        opened = await engine.open_session("primary", persistent=True)
        page_id = opened["page_id"]
        navigation = await engine.navigate("primary", page_id, fixture.origin)
        assert navigation["title"] == "CEO Fixture"

        extracted = await engine.extract("primary", page_id, max_characters=80)
        assert extracted["trust"] == "untrusted_page_content"
        assert extracted["truncated"] is True
        assert extracted["text"].startswith("Fixture Home")
        assert any(link["text"] == "Second page" for link in extracted["links"])
        assert {control["id"] for control in extracted["controls"]} >= {"name", "upload"}

        filled = await engine.fill(
            "primary", page_id, {"kind": "label", "value": "Name"}, "Abdullah"
        )
        assert filled["verified"] is True and filled["value_length"] == 8
        await engine.click(
            "primary",
            page_id,
            {"kind": "role", "value": "button", "name": "Change heading"},
        )
        changed = await engine.extract("primary", page_id, max_characters=100)
        assert changed["text"].startswith("Clicked")

        upload_file = tmp_path / "workspace/upload.txt"
        upload_file.write_text("scoped upload", encoding="utf-8")
        uploaded = await engine.upload(
            "primary", page_id, {"kind": "label", "value": "Upload"}, "upload.txt"
        )
        assert uploaded["filename"] == "upload.txt"

        downloaded = await engine.download(
            "primary", page_id, {"kind": "text", "value": "Download report"}
        )
        downloaded_text = await asyncio.to_thread(Path(downloaded["path"]).read_text)
        assert downloaded_text == "verified browser download"
        assert Path(downloaded["path"]).parent == (tmp_path / "workspace/downloads").resolve()

        await engine.click(
            "primary",
            page_id,
            {"kind": "role", "value": "button", "name": "Open popup"},
        )
        for _ in range(50):
            if len(engine.list_tabs("primary")["tabs"]) == 2:
                break
            await asyncio.sleep(0.01)
        assert len(engine.list_tabs("primary")["tabs"]) == 2

        assert "/pixel" not in external.requests
        with pytest.raises((BrowserPolicyError, PlaywrightError)):
            await engine.navigate("primary", page_id, f"{fixture.origin}/redirect-external")
        await engine.navigate("primary", page_id, fixture.origin)

        with pytest.raises(PlaywrightError, match="strict mode violation"):
            await engine.click(
                "primary",
                page_id,
                {"kind": "role", "value": "button", "name": "Duplicate"},
            )
    finally:
        await engine.shutdown()
        await fixture.close()
        await external.close()


@pytest.mark.asyncio
async def test_context_isolation_and_persistent_state_are_explicit(tmp_path: Path) -> None:
    fixture = FixtureServer()
    await fixture.start()
    engine = make_engine(tmp_path, {fixture.origin})
    await engine.start()
    try:
        first = await engine.open_session("first", persistent=True)
        await engine.open_session("second")
        await engine.navigate("first", first["page_id"], f"{fixture.origin}/set-cookie")
        first_cookie = await engine.visit("first", f"{fixture.origin}/cookie")
        second_cookie = await engine.visit("second", f"{fixture.origin}/cookie")
        assert "fixture_session=alpha" in first_cookie["text"]
        assert "Cookie: none" in second_cookie["text"]

        await engine.close_session("first")
        reopened = await engine.open_session("first", persistent=True)
        persisted = await engine.navigate("first", reopened["page_id"], f"{fixture.origin}/cookie")
        assert persisted["status"] == 200
        recalled = await engine.extract("first", reopened["page_id"])
        assert "fixture_session=alpha" in recalled["text"]
        state_file = tmp_path / "workspace/.ceo-os/browser/profiles/first.json"
        assert state_file.stat().st_mode & 0o777 == 0o600
    finally:
        await engine.shutdown()
        await fixture.close()


@pytest.mark.asyncio
async def test_stop_cancels_inflight_navigation_closes_sessions_and_does_not_replay(
    tmp_path: Path,
) -> None:
    fixture = FixtureServer()
    await fixture.start()
    engine = make_engine(tmp_path, {fixture.origin})
    await engine.start()
    try:
        opened = await engine.open_session("cancel")
        navigation = asyncio.create_task(
            engine.navigate("cancel", opened["page_id"], f"{fixture.origin}/slow")
        )
        await asyncio.wait_for(fixture.slow_started.wait(), timeout=2)
        stopped = await engine.stop()
        with pytest.raises(BrowserStoppedError):
            await navigation
        assert stopped["session_count"] == 0
        assert len([path for path in fixture.requests if path == "/slow"]) == 1
        with pytest.raises(BrowserStoppedError):
            await engine.open_session("blocked")
        engine.resume()
        assert len([path for path in fixture.requests if path == "/slow"]) == 1
    finally:
        await engine.shutdown()
        await fixture.close()


def test_browser_policy_rejects_unsafe_urls_paths_and_locators(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = BrowserPolicy(
        frozenset({"https://allowed.example"}), workspace, workspace / "downloads"
    )
    assert normalized_origin("https://ALLOWED.example/path") == "https://allowed.example"
    for url in (
        "file:///etc/passwd",
        "https://user:password@allowed.example",
        "https://allowed.example/path#fragment",
        "https://unlisted.example",
    ):
        with pytest.raises(BrowserPolicyError):
            policy.authorize_url(url)
    with pytest.raises(BrowserPolicyError, match="escapes"):
        policy.resolve_upload("../secret.txt")
    with pytest.raises(BrowserPolicyError):
        LocatorSpec.from_dict({"kind": "css", "value": "xpath=//button"})
    with pytest.raises(BrowserPolicyError):
        LocatorSpec.from_dict({"kind": "javascript", "value": "alert(1)"})


@pytest.mark.asyncio
async def test_effect_capabilities_are_absent_by_default_and_planner_uses_visit(
    tmp_path: Path,
) -> None:
    engine = make_engine(tmp_path, {"https://allowed.example"}, effects=False)
    safe_tools = browser_tools(engine)
    names = {tool.spec.name for tool in safe_tools}
    assert "browser.visit" in names
    assert "browser.click" not in names
    assert "browser.fill" not in names

    provider = DeterministicProvider()
    plan = await provider.plan(
        "Visit https://allowed.example/report", [tool.spec for tool in safe_tools]
    )
    assert [step.capability for step in plan.steps] == ["browser.visit"]
    assert plan.steps[0].arguments["url"] == "https://allowed.example/report"

    all_tools = browser_tools(engine, include_effects=True)
    risks = {tool.spec.name: tool.spec.risk for tool in all_tools}
    assert str(risks["browser.click"]) == "R2"
