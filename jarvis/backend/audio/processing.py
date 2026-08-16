"""Audio processing: RMS volume metering, Voice Activity Detection (VAD), and software AEC."""

from __future__ import annotations

import math
import struct


class AudioProcessor:
    """Processes raw PCM16 audio chunks for volume level, VAD energy, and echo reduction."""

    def __init__(
        self,
        echo_cancellation: bool = True,
        noise_suppression: bool = True,
        vad_threshold_rms: int = 400,
    ) -> None:
        self.echo_cancellation = echo_cancellation
        self.noise_suppression = noise_suppression
        self.vad_threshold_rms = vad_threshold_rms
        self._last_speaker_energy: float = 0.0

    @staticmethod
    def calculate_rms(pcm16_bytes: bytes) -> int:
        """Calculate Root Mean Square (RMS) amplitude of PCM16 audio."""
        if not pcm16_bytes or len(pcm16_bytes) < 2:
            return 0
        count = len(pcm16_bytes) // 2
        if count == 0:
            return 0
        shorts = struct.unpack(f"<{count}h", pcm16_bytes[: count * 2])
        sum_sq = sum(s * s for s in shorts)
        return int(math.sqrt(sum_sq / count))

    @staticmethod
    def get_meter_bars(rms: int, max_rms: int = 4000) -> str:
        """Return visual unicode volume meter: ▂▃▅▇▅▃"""
        levels = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        ratio = min(1.0, max(0.0, rms / max(1, max_rms)))
        idx = int(ratio * (len(levels) - 1))
        return levels[idx]

    def is_speech(self, pcm16_bytes: bytes) -> bool:
        """Determine if audio chunk contains active user voice above ambient noise floor."""
        rms = self.calculate_rms(pcm16_bytes)
        # If speaker was recently active and echo cancellation enabled, apply higher VAD threshold
        threshold = (
            self.vad_threshold_rms * 1.5
            if (self.echo_cancellation and self._last_speaker_energy > 0)
            else self.vad_threshold_rms
        )
        return rms >= threshold

    def notify_speaker_output(self, pcm16_bytes: bytes) -> None:
        """Notify processor of speaker playback energy for reference in AEC."""
        self._last_speaker_energy = self.calculate_rms(pcm16_bytes)

    def reset(self) -> None:
        self._last_speaker_energy = 0.0
