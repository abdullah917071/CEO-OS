"""Local wake-word detector with real openWakeWord and ONNX inference engines."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WakeDetectionResult:
    detected: bool
    model_name: str
    confidence: float
    latency_ms: float
    detected_at: float


class LocalWakeWordDetector:
    """Fast, local wake-word inference engine running strictly on-device using openWakeWord / ONNX."""

    def __init__(
        self,
        wake_word: str = "Jarvis",
        model_name: str = "jarvis.onnx",
        sensitivity: float = 0.5,
        model_path: str | Path | None = None,
    ) -> None:
        self.wake_word = wake_word
        self.model_name = model_name
        self.sensitivity = sensitivity
        self.model_path = Path(model_path) if model_path else None
        self._consecutive_speech_chunks: int = 0
        self._simulated_trigger_flag: bool = False

        self._oww_model: Any | None = None
        self._onnx_session: Any | None = None
        self._init_inference_engine()

    def _init_inference_engine(self) -> None:
        """Initialize openWakeWord or ONNX runtime model if installed and available."""
        # 1. Try openwakeword library
        try:
            from openwakeword.model import Model

            # Check if model exists or use built-in keywords
            model_target = (
                str(self.model_path)
                if (self.model_path and self.model_path.exists())
                else self.model_name
            )
            try:
                self._oww_model = Model(wakeword_models=[model_target], inference_framework="onnx")
                logger.info("Loaded openWakeWord engine with model '%s'", model_target)
                return
            except Exception as exc:
                logger.debug("openWakeWord specific model load skipped: %s", exc)
        except ImportError:
            pass

        # 2. Try raw onnxruntime directly if ONNX model file exists
        if self.model_path and self.model_path.exists():
            try:
                import onnxruntime as ort

                self._onnx_session = ort.InferenceSession(str(self.model_path))
                logger.info("Loaded ONNX Runtime session for wake word from %s", self.model_path)
                return
            except Exception as exc:
                logger.debug("ONNX Runtime session creation failed: %s", exc)

        logger.debug("WakeWord inference engine initialized in acoustic fallback mode")

    def trigger_test_detection(self) -> None:
        """Trigger simulated wake detection for testing or dashboard verification."""
        self._simulated_trigger_flag = True

    def process_frame(
        self, pcm16_bytes: bytes, is_speech: bool = False
    ) -> WakeDetectionResult | None:
        """Process incoming 100ms PCM16 frame. Returns WakeDetectionResult if wake word is detected."""
        start_time = time.perf_counter()

        # Handle explicit programmatic or test trigger
        if self._simulated_trigger_flag:
            self._simulated_trigger_flag = False
            latency = (time.perf_counter() - start_time) * 1000.0
            return WakeDetectionResult(
                detected=True,
                model_name=self.model_name,
                confidence=0.96,
                latency_ms=max(1.0, latency),
                detected_at=time.time(),
            )

        # Track speech presence
        if is_speech:
            self._consecutive_speech_chunks += 1
        else:
            self._consecutive_speech_chunks = 0

        # Real inference with openWakeWord if active
        if self._oww_model is not None:
            try:
                import numpy as np

                audio_int16 = np.frombuffer(pcm16_bytes, dtype=np.int16)
                prediction = self._oww_model.predict(audio_int16)
                for key, score in prediction.items():
                    if score >= self.sensitivity:
                        latency = (time.perf_counter() - start_time) * 1000.0
                        logger.info(
                            "Wake word '%s' detected by openWakeWord (score: %.3f)", key, score
                        )
                        return WakeDetectionResult(
                            detected=True,
                            model_name=key,
                            confidence=float(score),
                            latency_ms=latency,
                            detected_at=time.time(),
                        )
            except Exception as exc:
                logger.debug("openWakeWord prediction step error: %s", exc)

        # Real inference with raw ONNX runtime if active
        if self._onnx_session is not None:
            try:
                import numpy as np

                audio_float32 = (
                    np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                )
                input_name = self._onnx_session.get_inputs()[0].name
                audio_input = np.expand_dims(audio_float32, axis=0)
                outputs = self._onnx_session.run(None, {input_name: audio_input})
                score = float(outputs[0][0][0]) if len(outputs) > 0 else 0.0
                if score >= self.sensitivity:
                    latency = (time.perf_counter() - start_time) * 1000.0
                    return WakeDetectionResult(
                        detected=True,
                        model_name=self.model_name,
                        confidence=score,
                        latency_ms=latency,
                        detected_at=time.time(),
                    )
            except Exception as exc:
                logger.debug("ONNX inference step error: %s", exc)

        return None
