from __future__ import annotations

from core.contracts import ModelProvider


class ModelRouter:
    """Routes model roles without exposing provider details to the CEO runtime."""

    def __init__(self, providers: dict[str, ModelProvider], default_provider: str) -> None:
        if default_provider not in providers:
            raise ValueError(f"Unknown default model provider: {default_provider}")
        self._providers = providers
        self._default = default_provider

    def for_role(self, role: str = "ceo_planner") -> ModelProvider:
        del role  # Phase 1 has one configured route; later phases add policy-based routing.
        return self._providers[self._default]
