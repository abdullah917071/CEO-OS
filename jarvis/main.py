"""Standalone runner and CLI entrypoint for Jarvis macOS Voice Assistant."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from jarvis.backend.agent.manager import JarvisAgentManager
from jarvis.backend.config.settings import JarvisSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis")


async def main() -> None:
    print("=" * 65)
    print("   🎙️  JARVIS — macOS Desktop Voice Assistant (Gemini Live)")
    print("=" * 65)
    print("• Wake word: 'Jarvis' (Local-first offline detection)")
    print("• Realtime Voice: Gemini Live API (Bidirectional WebSockets)")
    print("• Idle cost: $0.00 (Gemini disconnected while idle)")
    print("=" * 65)

    settings = JarvisSettings()
    settings.ensure_directories()

    manager = JarvisAgentManager(settings=settings)
    manager.start()

    stop_event = asyncio.Event()

    def _handle_signal(*args: object) -> None:
        logger.info("Received termination signal. Shutting down...")
        manager.stop()
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_signal)
        except Exception:
            pass

    print(f"\n[JARVIS READY] Listening locally for '{settings.wakeword.wake_word}'...")
    print("Press Ctrl+C to quit.\n")

    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        manager.stop()

    print("\n[JARVIS SHUTDOWN] Good evening, sir.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
