"""Wake-word manager orchestrating local detection lifecycle."""

from __future__ import annotations

import logging
from collections.abc import Callable

from jarvis.backend.config.settings import WakeWordConfig
from jarvis.backend.wakeword.detector import LocalWakeWordDetector, WakeDetectionResult

logger = logging.getLogger(__name__)


class WakeWordManager:
    """Manages start/stop, threshold configuration, and activation callbacks."""

    def __init__(
        self,
        config: WakeWordConfig,
        on_wake_detected: Callable[[WakeDetectionResult], None] | None = None,
    ) -> None:
        self.config = config
        self.on_wake_detected = on_wake_detected
        self.detector = LocalWakeWordDetector(
            wake_word=config.wake_word,
            model_name=config.model_name,
            sensitivity=config.sensitivity,
        )
        self._is_active: bool = True

    @property
    def is_active(self) -> bool:
        return self._is_active

    def start(self) -> None:
        """Start listening for local wake word."""
        self._is_active = True
        logger.info(
            "WakeWordManager listening for '%s' (%s)",
            self.config.wake_word,
            self.config.model_name,
        )

    def pause(self) -> None:
        """Pause wake word detection while Gemini Live is in ACTIVE state."""
        self._is_active = False
        logger.info("WakeWordManager paused (active Gemini session)")

    def resume(self) -> None:
        """Resume wake word detection when Gemini session ends."""
        self._is_active = True
        logger.info("WakeWordManager resumed listening for '%s'", self.config.wake_word)

    def stop(self) -> None:
        """Stop wake word manager completely."""
        self._is_active = False

    def update_config(self, config: WakeWordConfig) -> None:
        """Hot-reload wake-word configuration."""
        self.config = config
        self.detector = LocalWakeWordDetector(
            wake_word=config.wake_word,
            model_name=config.model_name,
            sensitivity=config.sensitivity,
        )
        logger.info(
            "Reloaded wake word: '%s', model: '%s', sensitivity: %.2f",
            config.wake_word,
            config.model_name,
            config.sensitivity,
        )

    def process_audio_frame(
        self, pcm16_bytes: bytes, is_speech: bool = False
    ) -> WakeDetectionResult | None:
        """Evaluate audio frame locally. Dispatches callback if phrase detected."""
        if not self._is_active or not self.config.require_wake_word:
            return None

        result = self.detector.process_frame(pcm16_bytes, is_speech=is_speech)
        if result and result.detected:
            logger.info(
                "Local wake word detected: '%s' (confidence: %.2f)",
                self.config.wake_word,
                result.confidence,
            )
            if self.on_wake_detected:
                try:
                    self.on_wake_detected(result)
                except Exception as exc:
                    logger.error("Error executing wake detected callback: %s", exc)
        return result
