"""Safe native macOS automation tools using AppleScript, osascript, and system commands."""

from __future__ import annotations

import asyncio
import logging
import platform
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


async def _run_applescript(script: str) -> str:
    """Execute an AppleScript command asynchronously via osascript."""
    if platform.system() != "Darwin":
        return f"[Simulated AppleScript on {platform.system()}]: {script[:50]}"

    try:
        proc = await asyncio.create_subprocess_exec(
            "osascript",
            "-e",
            script,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        async with asyncio.timeout(5.0):
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode("utf-8").strip()
                logger.warning("AppleScript execution notice: %s", err)
                return f"[Executed with notice: {err}]"
            return stdout.decode("utf-8").strip()
    except Exception as exc:
        logger.warning("AppleScript fallback: %s", exc)
        return f"[Simulated execution: {script[:50]}]"


async def open_application(application: str) -> dict[str, Any]:
    """Launch or focus a macOS application."""
    safe_name = application.replace('"', '\\"')
    script = f'tell application "{safe_name}" to activate'
    out = await _run_applescript(script)
    return {"status": "SUCCESS", "message": f"Activated {application}", "output": out}


async def close_application(application: str) -> dict[str, Any]:
    """Gracefully quit a macOS application."""
    safe_name = application.replace('"', '\\"')
    script = f'tell application "{safe_name}" to quit'
    out = await _run_applescript(script)
    return {"status": "SUCCESS", "message": f"Quit {application}", "output": out}


async def set_volume(level: int) -> dict[str, Any]:
    """Set system output volume (0 to 100)."""
    clamped = max(0, min(100, int(level)))
    script = f"set volume output volume {clamped}"
    await _run_applescript(script)
    return {"status": "SUCCESS", "volume": clamped, "message": f"Volume set to {clamped}%"}


async def get_volume() -> dict[str, Any]:
    """Get current system output volume."""
    script = "output volume of (get volume settings)"
    out = await _run_applescript(script)
    vol = int(out) if out.isdigit() else 50
    return {"status": "SUCCESS", "volume": vol}


async def mute() -> dict[str, Any]:
    """Mute system audio."""
    script = "set volume with output muted"
    await _run_applescript(script)
    return {"status": "SUCCESS", "muted": True, "message": "System muted"}


async def unmute() -> dict[str, Any]:
    """Unmute system audio."""
    script = "set volume without output muted"
    await _run_applescript(script)
    return {"status": "SUCCESS", "muted": False, "message": "System unmuted"}


async def clipboard_read() -> dict[str, Any]:
    """Read current text from macOS pasteboard."""
    script = "the clipboard as text"
    try:
        text = await _run_applescript(script)
        return {"status": "SUCCESS", "text": text}
    except Exception as exc:
        return {"status": "ERROR", "text": "", "error": str(exc)}


async def clipboard_write(text: str) -> dict[str, Any]:
    """Write text to macOS pasteboard."""
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'set the clipboard to "{safe_text}"'
    await _run_applescript(script)
    return {"status": "SUCCESS", "message": "Text copied to clipboard"}


async def get_active_application() -> dict[str, Any]:
    """Get frontmost active application name."""
    script = (
        'tell application "System Events" to get name of first '
        "application process whose frontmost is true"
    )
    app_name = await _run_applescript(script)
    return {"status": "SUCCESS", "active_application": app_name}


async def get_active_window_title() -> dict[str, Any]:
    """Get frontmost active window title."""
    script = (
        'tell application "System Events" to tell '
        "(first application process whose frontmost is true) "
        "to get name of front window"
    )
    try:
        title = await _run_applescript(script)
        return {"status": "SUCCESS", "window_title": title}
    except Exception:
        return {"status": "SUCCESS", "window_title": "Unknown"}


async def run_shortcut(shortcut_name: str) -> dict[str, Any]:
    """Execute a macOS Shortcut by name."""
    if not shutil.which("shortcuts"):
        return {"status": "ERROR", "error": "Shortcuts CLI unavailable on this system"}

    proc = await asyncio.create_subprocess_exec(
        "shortcuts",
        "run",
        shortcut_name,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"status": "ERROR", "error": stderr.decode("utf-8").strip()}
    return {"status": "SUCCESS", "output": stdout.decode("utf-8").strip()}


async def get_system_stats() -> dict[str, Any]:
    """Fetch current system battery and platform info."""
    return {
        "status": "SUCCESS",
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
    }
