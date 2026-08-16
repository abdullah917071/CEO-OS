"""Media playback and Spotify control tools for Jarvis."""

from __future__ import annotations

from typing import Any

from jarvis.backend.tools.macos import _run_applescript, open_application


async def open_spotify() -> dict[str, Any]:
    """Launch or bring Spotify to foreground."""
    return await open_application("Spotify")


async def play_pause_media() -> dict[str, Any]:
    """Toggle play/pause state of active media (Spotify or Music)."""
    script = """
    if application "Spotify" is running then
        tell application "Spotify" to playpause
        return "Spotify toggled"
    else if application "Music" is running then
        tell application "Music" to playpause
        return "Music toggled"
    else
        tell application "Spotify" to activate
        return "Started Spotify"
    end if
    """
    out = await _run_applescript(script)
    return {"status": "SUCCESS", "message": out}


async def next_track() -> dict[str, Any]:
    """Skip to next media track."""
    script = """
    if application "Spotify" is running then
        tell application "Spotify" to next track
        return "Spotify skipped to next track"
    else if application "Music" is running then
        tell application "Music" to next track
        return "Music skipped to next track"
    else
        return "No active media player running"
    end if
    """
    out = await _run_applescript(script)
    return {"status": "SUCCESS", "message": out}


async def previous_track() -> dict[str, Any]:
    """Go back to previous media track."""
    script = """
    if application "Spotify" is running then
        tell application "Spotify" to previous track
        return "Spotify returned to previous track"
    else if application "Music" is running then
        tell application "Music" to previous track
        return "Music returned to previous track"
    else
        return "No active media player running"
    end if
    """
    out = await _run_applescript(script)
    return {"status": "SUCCESS", "message": out}
