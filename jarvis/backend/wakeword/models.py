"""Wake word model definitions, registry, and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WakeWordModelInfo:
    display_name: str
    model_filename: str
    description: str
    is_installed: bool
    default_threshold: float = 0.5


AVAILABLE_WAKE_MODELS: list[WakeWordModelInfo] = [
    WakeWordModelInfo(
        display_name="Jarvis",
        model_filename="jarvis.onnx",
        description="Default production wake-word model for Jarvis",
        is_installed=True,
        default_threshold=0.5,
    ),
    WakeWordModelInfo(
        display_name="Computer",
        model_filename="computer.onnx",
        description="Star Trek inspired computer activation model",
        is_installed=True,
        default_threshold=0.5,
    ),
    WakeWordModelInfo(
        display_name="Friday",
        model_filename="friday.onnx",
        description="Marvel Friday assistant wake model",
        is_installed=True,
        default_threshold=0.5,
    ),
    WakeWordModelInfo(
        display_name="Assistant",
        model_filename="assistant.onnx",
        description="Neutral assistant activation model",
        is_installed=True,
        default_threshold=0.5,
    ),
    WakeWordModelInfo(
        display_name="Hey Nova",
        model_filename="hey_nova.onnx",
        description="Modern conversational voice trigger",
        is_installed=True,
        default_threshold=0.5,
    ),
]


def list_available_models(model_dir: Path | None = None) -> list[WakeWordModelInfo]:
    """Return all catalog models and any custom user-uploaded models."""
    results = list(AVAILABLE_WAKE_MODELS)
    if model_dir and model_dir.exists():
        for file in model_dir.glob("*.onnx"):
            if not any(m.model_filename == file.name for m in results):
                name = file.stem.title().replace("_", " ")
                results.append(
                    WakeWordModelInfo(
                        display_name=name,
                        model_filename=file.name,
                        description=f"Custom uploaded wake model: {file.name}",
                        is_installed=True,
                        default_threshold=0.5,
                    )
                )
    return results
