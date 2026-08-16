"""Standalone CEO OS Computer-Use Agent (CUA) Desktop Application."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from apps.desktop.contracts import CuaActionResult, CuaAppInfo, CuaDesktopState
from ceo_agent.agent import CeoAIAgent
from ceo_agent.llm import OpenAiCompatibleCeoEngine
from computer.client import MacHelperClient
from computer.controller import ComputerController, ComputerPolicy


class CuaDesktopApp:
    """Standalone CEO OS Computer-Use Agent (CUA) host controller."""

    def __init__(
        self,
        helper_path: Path | None = None,
        *,
        effects_enabled: bool = True,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        self.helper_path = (
            helper_path.resolve()
            if helper_path and helper_path.is_absolute()
            else (
                (base_dir / helper_path).resolve()
                if helper_path
                else base_dir / "computer/macos_helper/.build/release/ceo-os-mac-helper"
            )
        )
        self.client = MacHelperClient(self.helper_path)
        self.controller = ComputerController(
            self.client,
            ComputerPolicy(effects_enabled=effects_enabled),
        )

    async def list_applications(self) -> list[CuaAppInfo]:
        """List all installed and running applications on the macOS host."""
        if not self.client.supported:
            return []
        try:
            res = await self.client.request("list_apps")
            apps = res.get("applications", res.get("apps", []))
            return [
                CuaAppInfo(
                    bundle_id=a.get("bundle_id", ""),
                    name=a.get("name", ""),
                    path=a.get("path", ""),
                    running=a.get("running", False),
                    frontmost=a.get("frontmost", False),
                    pid=a.get("pid"),
                )
                for a in apps
            ]
        except Exception:
            return []

    async def get_desktop_state(self) -> CuaDesktopState:
        """Capture current frontmost app and desktop runtime state."""
        apps = await self.list_applications()
        frontmost = next((a.name for a in apps if a.frontmost), "Desktop")
        running_count = sum(1 for a in apps if a.running)
        return CuaDesktopState(
            running_apps_count=running_count,
            frontmost_app=frontmost,
            accessibility_granted=True,
        )

    async def focus_application(self, target: str) -> CuaActionResult:
        """Bring an application to the foreground by bundle ID or display name."""
        if not self.client.supported:
            return CuaActionResult(
                action="focus_app",
                success=False,
                error="macOS helper is not supported in this environment",
            )
        apps = await self.list_applications()
        matched = None
        target_lower = target.lower().strip()
        for a in apps:
            if a.bundle_id.lower() == target_lower or a.name.lower() == target_lower:
                matched = a
                break

        bundle_id = matched.bundle_id if matched else target
        try:
            res = await self.client.request("focus_app", bundle_id=bundle_id)
            return CuaActionResult(
                action="focus_app",
                success=True,
                output=res,
            )
        except Exception as exc:
            return CuaActionResult(
                action="focus_app",
                success=False,
                error=str(exc),
            )

    async def type_text(self, text: str) -> CuaActionResult:
        """Type text into the frontmost focused application."""
        if not self.client.supported:
            return CuaActionResult(
                action="type_text",
                success=False,
                error="macOS helper is not supported in this environment",
            )
        try:
            res = await self.client.request("type_text", text=text)
            return CuaActionResult(
                action="type_text",
                success=True,
                output=res,
            )
        except Exception as exc:
            return CuaActionResult(
                action="type_text",
                success=False,
                error=str(exc),
            )

    async def press_key(self, key: str, modifiers: list[str] | None = None) -> CuaActionResult:
        """Send a keyboard shortcut to the frontmost application."""
        if not self.client.supported:
            return CuaActionResult(
                action="press_key",
                success=False,
                error="macOS helper is not supported in this environment",
            )
        try:
            res = await self.client.request("key_press", key=key, modifiers=modifiers or [])
            return CuaActionResult(
                action="press_key",
                success=True,
                output=res,
            )
        except Exception as exc:
            return CuaActionResult(
                action="press_key",
                success=False,
                error=str(exc),
            )

    async def execute_autonomous_directive(self, directive: str) -> dict[str, Any]:
        """Run autonomous CEO OS CUA ReAct reasoning loop on desktop."""
        api_key = os.getenv(
            "CEO_OS_REASONING_API_KEY",
            os.getenv(
                "CEO_OS_OPENROUTER_API_KEY",
                os.getenv("OPENROUTER_API_KEY", ""),
            ),
        )
        model = os.getenv("CEO_OS_MODEL_NAME", "nvidia/nemotron-3.5-lightning:free")
        engine = (
            OpenAiCompatibleCeoEngine(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                model_name=model,
            )
            if api_key
            else None
        )
        agent = CeoAIAgent(llm=engine)
        res = await agent.run(task_id="cua_task", objective=directive)
        return {
            "status": res.status,
            "final_answer": res.final_answer,
            "steps_count": len(res.trajectory.steps),
            "duration_ms": res.duration_ms,
        }


async def interactive_cli() -> None:
    """Interactive CLI REPL for the standalone CEO OS CUA Desktop Controller."""
    app = CuaDesktopApp()
    print("=" * 65)
    print("  🖥️  CEO OS — Standalone Computer-Use Agent (CUA) Controller")
    print("=" * 65)
    print("Commands:")
    print("  apps                 - List all running and installed macOS apps")
    print("  state                - Get current desktop perception state")
    print("  focus <app_name>     - Focus application (e.g. 'focus Safari')")
    print("  type <text>          - Type text into focused window")
    print("  key <key> [mod...]   - Send key shortcut (e.g. 'key return')")
    print("  task <directive>     - Run autonomous CUA reasoning loop")
    print("  exit / quit          - Exit CUA Controller")
    print("=" * 65)

    while True:
        try:
            line = (await asyncio.to_thread(input, "\n[CEO-OS:CUA] > ")).strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "q"):
                print("Exiting CUA Controller.")
                break

            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "apps":
                apps = await app.list_applications()
                running = [a for a in apps if a.running]
                print(f"\n--- Running Applications ({len(running)}) ---")
                for a in running:
                    indicator = "🟢 [FRONT]" if a.frontmost else "⚪"
                    print(f"  {indicator} {a.name:<25} ({a.bundle_id})")
            elif cmd == "state":
                state = await app.get_desktop_state()
                print(
                    f"\nDesktop State: Frontmost = '{state.frontmost_app}', "
                    f"Running Apps = {state.running_apps_count}"
                )
            elif cmd == "focus":
                if not arg:
                    print("Usage: focus <app_name>")
                    continue
                res = await app.focus_application(arg)
                print(f"Focus result: {res}")
            elif cmd == "type":
                if not arg:
                    print("Usage: type <text>")
                    continue
                res = await app.type_text(arg)
                print(f"Type result: {res}")
            elif cmd == "key":
                if not arg:
                    print("Usage: key <key_name>")
                    continue
                res = await app.press_key(arg)
                print(f"Key result: {res}")
            elif cmd == "task":
                if not arg:
                    print("Usage: task <objective>")
                    continue
                print(f"Executing autonomous CUA task: '{arg}'...")
                res_dict = await app.execute_autonomous_directive(arg)
                print(f"Task result: {res_dict}")
            else:
                print(f"Unknown command: '{cmd}'. Try 'apps', 'state', 'focus', 'type', 'key'.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CUA Controller.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="CEO OS Standalone CUA Desktop Host Controller")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Launch interactive CLI REPL"
    )
    parser.add_argument("--focus", type=str, help="Focus application by name or bundle ID")
    parser.add_argument(
        "--type", type=str, dest="type_text", help="Type text into frontmost application"
    )
    parser.add_argument("--list-apps", action="store_true", help="List running applications")
    args = parser.parse_args()

    app = CuaDesktopApp()

    if args.list_apps:
        apps = asyncio.run(app.list_applications())
        for a in [app_item for app_item in apps if app_item.running]:
            print(f"{a.name} ({a.bundle_id})")
    elif args.focus:
        res = asyncio.run(app.focus_application(args.focus))
        print(res)
    elif args.type_text:
        res = asyncio.run(app.type_text(args.type_text))
        print(res)
    else:
        asyncio.run(interactive_cli())


if __name__ == "__main__":
    main()
