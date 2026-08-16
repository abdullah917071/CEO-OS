from __future__ import annotations

from agents.contracts import AgentBudget, AgentTemplate


class AgentTemplateRegistry:
    def __init__(self) -> None:
        self._templates = {
            template.name: template
            for template in (
                AgentTemplate(
                    "researcher",
                    1,
                    "Research Worker",
                    frozenset({"web.search", "browser.read"}),
                    frozenset({"assignment"}),
                    "medium_reasoning",
                    False,
                    AgentBudget(1_800, 100, 1),
                ),
                AgentTemplate(
                    "analyst",
                    1,
                    "Analyst",
                    frozenset({"data.read"}),
                    frozenset({"assignment"}),
                    "medium_reasoning",
                    False,
                    AgentBudget(1_200, 100, 1),
                ),
                AgentTemplate(
                    "developer",
                    1,
                    "Developer",
                    frozenset({"files.read", "files.write"}),
                    frozenset({"workspace"}),
                    "coding",
                    False,
                    AgentBudget(1_800, 200, 1),
                ),
                AgentTemplate(
                    "verifier",
                    1,
                    "Verifier",
                    frozenset({"evidence.read"}),
                    frozenset({"assignment"}),
                    "medium_reasoning",
                    False,
                    AgentBudget(600, 50, 1),
                ),
            )
        }

    def get(self, name: str) -> AgentTemplate:
        try:
            return self._templates[name]
        except KeyError as exc:
            raise ValueError(f"Unknown agent template: {name}") from exc

    def list(self) -> list[AgentTemplate]:
        return list(self._templates.values())
