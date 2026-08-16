"""Lazy and cached loader for discovering and parsing AgentDefinitions from filesystem."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from agents.registry.contracts import AgentDefinition, AgentProviderSource
from agents.registry.parser import parse_agent_file

logger = logging.getLogger(__name__)


class AgentLoader:
    """Discovers, parses, and caches agent definition files across multiple root directories."""

    def __init__(self, search_roots: Sequence[str | Path] | None = None) -> None:
        self._roots: list[Path] = []
        if search_roots:
            self._roots.extend([Path(p).expanduser().resolve() for p in search_roots])
        else:
            default_paths = [
                Path("~/.gemini/config/skills").expanduser().resolve(),
                Path(".agents/skills").resolve(),
                Path("vendor/agency-agents").resolve(),
                Path("agents/custom").resolve(),
            ]
            for p in default_paths:
                if p.exists() and p.is_dir():
                    self._roots.append(p)

        self._cache: dict[str, AgentDefinition] = {}
        self._loaded: bool = False

    def load_all(self, force_reload: bool = False) -> dict[str, AgentDefinition]:
        """Scan search roots and return all parsed agent definitions."""
        if self._loaded and not force_reload:
            return self._cache

        self._cache.clear()
        found = 0

        for root in self._roots:
            if not root.exists() or not root.is_dir():
                continue

            for child in root.iterdir():
                if not child.is_dir():
                    continue

                # Check SKILL.md, AGENT.md, or {name}.md
                skill_md = child / "SKILL.md"
                agent_md = child / "AGENT.md"
                target_file = (
                    skill_md if skill_md.exists() else (agent_md if agent_md.exists() else None)
                )

                if target_file:
                    defn = parse_agent_file(target_file, source=AgentProviderSource.AGENCY)
                    if defn:
                        self._cache[defn.id] = defn
                        # Also alias without 'agency-' prefix for convenient retrieval
                        clean_alias = defn.id.replace("agency-", "")
                        if clean_alias != defn.id and clean_alias not in self._cache:
                            self._cache[clean_alias] = defn
                        found += 1

        self._loaded = True
        logger.info("AgentLoader discovered %d agent personas across roots: %s", found, self._roots)
        return self._cache

    def get(self, agent_id: str) -> AgentDefinition | None:
        """Retrieve a specific agent definition by id (case-insensitive)."""
        if not self._loaded:
            self.load_all()
        clean = agent_id.strip().lower()
        if clean in self._cache:
            return self._cache[clean]
        if f"agency-{clean}" in self._cache:
            return self._cache[f"agency-{clean}"]
        return None
