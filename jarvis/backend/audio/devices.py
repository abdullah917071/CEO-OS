"""Audio device enumeration for macOS and CoreAudio."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AudioDeviceInfo:
    id: str
    name: str
    is_input: bool
    is_output: bool
    channels: int
    default_sample_rate: int


def list_audio_devices() -> dict[str, list[AudioDeviceInfo]]:
    """List available audio input and output devices using sounddevice or fallback defaults."""
    inputs: list[AudioDeviceInfo] = []
    outputs: list[AudioDeviceInfo] = []

    try:
        import sounddevice as sd  # type: ignore[import-untyped]

        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            max_in = int(dev.get("max_input_channels", 0))
            max_out = int(dev.get("max_output_channels", 0))
            name = str(dev.get("name", f"Device {idx}"))
            sr = int(dev.get("default_samplerate", 16000))

            if max_in > 0:
                inputs.append(
                    AudioDeviceInfo(
                        id=str(idx),
                        name=name,
                        is_input=True,
                        is_output=False,
                        channels=max_in,
                        default_sample_rate=sr,
                    )
                )
            if max_out > 0:
                outputs.append(
                    AudioDeviceInfo(
                        id=str(idx),
                        name=name,
                        is_input=False,
                        is_output=True,
                        channels=max_out,
                        default_sample_rate=sr,
                    )
                )
    except Exception as exc:
        logger.debug("sounddevice query unavailable (%s), using standard macOS defaults", exc)
        inputs.append(
            AudioDeviceInfo(
                id="default",
                name="MacBook / Mac Mini Built-in Microphone",
                is_input=True,
                is_output=False,
                channels=1,
                default_sample_rate=16000,
            )
        )
        outputs.append(
            AudioDeviceInfo(
                id="default",
                name="MacBook / Mac Mini Built-in Speakers",
                is_input=False,
                is_output=True,
                channels=2,
                default_sample_rate=24000,
            )
        )

    return {"inputs": inputs, "outputs": outputs}
