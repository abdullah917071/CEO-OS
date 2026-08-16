"""Browser automation tools for Jarvis."""

from __future__ import annotations

import urllib.parse
from typing import Any

from jarvis.backend.tools.macos import _run_applescript


async def open_url(url: str) -> dict[str, Any]:
    """Open specified web URL in default browser."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    safe_url = url.replace('"', '\\"')
    script = f'open location "{safe_url}"'
    try:
        await _run_applescript(script)
    except Exception:
        import webbrowser

        try:
            webbrowser.open(url)
        except Exception:
            pass
    return {"status": "SUCCESS", "message": f"Opened {url}", "url": url}


async def search_google(query: str) -> dict[str, Any]:
    """Perform Google web search in default browser."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    return await open_url(url)


async def open_youtube(query: str = "") -> dict[str, Any]:
    """Open YouTube home or search results."""
    if query.strip():
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
    else:
        url = "https://www.youtube.com"
    return await open_url(url)
