"""Agent Spawner: instantiates and activates real worker execution contexts from AgentDefinitions."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from agents.contracts import AgentBudget, AgentKind, AgentStatus
from agents.registry.contracts import AgentDefinition

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ActiveWorkerContext:
    """Live runtime context for a spawned worker."""

    instance_id: str
    definition: AgentDefinition
    kind: AgentKind
    status: AgentStatus
    allowed_capabilities: set[str]
    assigned_tools: list[str]
    budget: AgentBudget
    memory_scope: str
    parent_id: str | None = None
    created_at: float = field(default_factory=lambda: __import__("time").time())


class AgentSpawner:
    """Spawns scoped runtime instances of agent personas with permissions and tool attachments."""

    def __init__(self) -> None:
        self._active_workers: dict[str, ActiveWorkerContext] = {}

    def spawn(
        self,
        definition: AgentDefinition,
        parent_id: str | None = None,
        custom_tools: list[str] | None = None,
        budget: AgentBudget | None = None,
        kind: AgentKind = AgentKind.TEMPORARY,
    ) -> ActiveWorkerContext:
        """Instantiate an active worker from an agent definition."""
        instance_id = f"worker_{definition.id}_{uuid.uuid4().hex[:8]}"

        tools = custom_tools if custom_tools is not None else list(definition.default_tools)
        caps = set(definition.allowed_capabilities).union(tools)

        effective_budget = budget or AgentBudget(
            max_runtime_seconds=1800,
            max_cost_units=100,
            max_concurrency=1,
        )

        ctx = ActiveWorkerContext(
            instance_id=instance_id,
            definition=definition,
            kind=kind,
            status=AgentStatus.ACTIVE,
            allowed_capabilities=caps,
            assigned_tools=tools,
            budget=effective_budget,
            memory_scope=f"worker:{instance_id}",
            parent_id=parent_id,
        )

        self._active_workers[instance_id] = ctx
        logger.info("Spawned worker %s for agent persona %s", instance_id, definition.id)
        return ctx

    def terminate(self, instance_id: str) -> None:
        """Mark a temporary worker as terminated and release resources."""
        ctx = self._active_workers.get(instance_id)
        if ctx:
            ctx.status = AgentStatus.TERMINATED
            logger.info("Terminated worker %s", instance_id)

    def get(self, instance_id: str) -> ActiveWorkerContext | None:
        return self._active_workers.get(instance_id)
