"""Agent Router Primitive Tools exposed to CEO ReAct loop and Runtime."""

from __future__ import annotations

import logging
from typing import Any

from agents.registry.agency_registry import UniversalAgentRegistry
from agents.registry.contracts import AgentDivision
from agents.runtime.delegation import StructuredTaskMessage, TaskConstraints
from agents.runtime.execution import SpecialistWorkerExecutor
from agents.runtime.spawner import AgentSpawner
from agents.runtime.team import TeamOrchestrator
from core.contracts import CapabilitySpec, RiskLevel, ToolResult

logger = logging.getLogger(__name__)

# Shared global registry instance
_default_registry: UniversalAgentRegistry | None = None


def get_global_agent_registry() -> UniversalAgentRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = UniversalAgentRegistry()
    return _default_registry


# ── 1. agent.search ────────────────────────────────────────────────────────────


class AgentSearchTool:
    """Tool allowing CEO to dynamically search the 270+ specialist agent roster."""

    def __init__(self, registry: UniversalAgentRegistry | None = None) -> None:
        self.registry = registry or get_global_agent_registry()

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agent.search",
            "Search the specialist agent roster by task intent or division without preloading all personas into prompt.",
            {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task objective or specialist skill needed",
                    },
                    "division": {
                        "type": "string",
                        "description": "Optional division filter (engineering, marketing, sales, finance, operations, product, security, design, research, communications)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of candidate matches to return",
                        "default": 5,
                    },
                },
            },
            RiskLevel.READ,
            source="agent_router",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        query = str(arguments.get("query", ""))
        div_str = arguments.get("division")
        limit_val = arguments.get("limit", 5)
        limit = int(str(limit_val)) if isinstance(limit_val, (int, str)) else 5

        division: AgentDivision | None = None
        if div_str and isinstance(div_str, str):
            try:
                division = AgentDivision(div_str.lower())
            except ValueError:
                pass

        matches = await self.registry.search(query, division=division, limit=limit)
        results = [
            {
                "agent_id": m.agent.id,
                "name": m.agent.name,
                "role": m.agent.role,
                "division": m.agent.division.value,
                "relevance_score": m.relevance_score,
                "match_reasons": m.match_reasons,
                "default_tools": m.agent.default_tools,
                "score_rating": m.agent.score.owner_rating,
                "success_rate": m.agent.score.success_rate,
            }
            for m in matches
        ]

        evidence = [f"Found {len(results)} candidate agents for '{query}'"]
        if results:
            evidence.append(
                f"Top candidate: {results[0]['name']} ({results[0]['role']}) [Score: {results[0]['relevance_score']}]"
            )

        return ToolResult(
            {"query": query, "count": len(results), "candidates": results},
            evidence,
        )


# ── 2. agent.inspect ───────────────────────────────────────────────────────────


class AgentInspectTool:
    """Tool allowing CEO to inspect an agent's full persona, mission, rules, and capabilities."""

    def __init__(self, registry: UniversalAgentRegistry | None = None) -> None:
        self.registry = registry or get_global_agent_registry()

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agent.inspect",
            "Inspect full persona instructions, capabilities, rules, and scoring for an agent id.",
            {
                "type": "object",
                "required": ["agent_id"],
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The exact ID of the agent to inspect",
                    },
                },
            },
            RiskLevel.READ,
            source="agent_router",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        agent_id = str(arguments.get("agent_id", ""))
        agent = await self.registry.get_agent(agent_id)

        if not agent:
            return ToolResult(
                {"error": f"Agent '{agent_id}' not found in registry", "status": "NOT_FOUND"},
                [f"Agent '{agent_id}' not found"],
            )

        output = {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "division": agent.division.value,
            "description": agent.description,
            "source": agent.source.value,
            "tags": agent.tags,
            "default_tools": agent.default_tools,
            "allowed_capabilities": agent.allowed_capabilities,
            "is_permanent": agent.is_permanent,
            "model_class": agent.model_class,
            "score": {
                "tasks_completed": agent.score.tasks_completed,
                "success_rate": agent.score.success_rate,
                "average_confidence": agent.score.average_confidence,
                "owner_rating": agent.score.owner_rating,
            },
            "instructions_preview": agent.instructions[:800],
        }

        return ToolResult(output, [f"Inspected agent persona: {agent.name} ({agent.role})"])


# ── 3. agent.spawn ─────────────────────────────────────────────────────────────


class AgentSpawnTool:
    """Tool allowing CEO to spawn a scoped worker instance with custom tool attachments."""

    def __init__(
        self,
        registry: UniversalAgentRegistry | None = None,
        spawner: AgentSpawner | None = None,
    ) -> None:
        self.registry = registry or get_global_agent_registry()
        self.spawner = spawner or AgentSpawner()

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agent.spawn",
            "Spawn an active worker instance of an agent persona with scoped permissions and tools.",
            {
                "type": "object",
                "required": ["agent_id"],
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to instantiate"},
                    "custom_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tool bindings",
                    },
                    "max_runtime_seconds": {
                        "type": "integer",
                        "description": "Runtime timeout limit",
                        "default": 1800,
                    },
                },
            },
            RiskLevel.HARMLESS_WRITE,
            source="agent_router",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        agent_id = str(arguments.get("agent_id", ""))
        custom_tools = arguments.get("custom_tools")
        tools_list = [str(t) for t in custom_tools] if isinstance(custom_tools, list) else None

        agent = await self.registry.get_agent(agent_id)
        if not agent:
            return ToolResult(
                {"error": f"Agent '{agent_id}' not found", "status": "NOT_FOUND"},
                ["Agent not found"],
            )

        worker = self.spawner.spawn(agent, custom_tools=tools_list)
        return ToolResult(
            {
                "instance_id": worker.instance_id,
                "agent_id": agent.id,
                "name": agent.name,
                "assigned_tools": worker.assigned_tools,
                "allowed_capabilities": list(worker.allowed_capabilities),
                "status": worker.status.value,
            },
            [f"Spawned active worker: {worker.instance_id} for {agent.name}"],
        )


# ── 4. agent.delegate ──────────────────────────────────────────────────────────


class AgentDelegateTool:
    """Tool allowing CEO to delegate a task to a specialist agent and receive structured deliverables."""

    def __init__(
        self,
        registry: UniversalAgentRegistry | None = None,
        spawner: AgentSpawner | None = None,
        executor: SpecialistWorkerExecutor | None = None,
    ) -> None:
        self.registry = registry or get_global_agent_registry()
        self.spawner = spawner or AgentSpawner()
        self.executor = executor or SpecialistWorkerExecutor()

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agent.delegate",
            "Delegate a structured task to a specialist agent and collect findings, deliverables, and evidence.",
            {
                "type": "object",
                "required": ["agent_id", "task"],
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Specialist agent ID to execute the task",
                    },
                    "task": {"type": "string", "description": "Clear task directive"},
                    "deliverable": {
                        "type": "string",
                        "description": "Expected deliverable name",
                        "default": "analysis_and_plan",
                    },
                    "do_not_modify_production": {"type": "boolean", "default": True},
                },
            },
            RiskLevel.HARMLESS_WRITE,
            source="agent_router",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        agent_id = str(arguments.get("agent_id", ""))
        task_text = str(arguments.get("task", ""))
        deliverable = str(arguments.get("deliverable", "analysis_and_plan"))
        no_prod = bool(arguments.get("do_not_modify_production", True))

        agent = await self.registry.get_agent(agent_id)
        if not agent:
            # Fallback search
            matches = await self.registry.search(agent_id, limit=1)
            if matches:
                agent = matches[0].agent

        if not agent:
            return ToolResult(
                {"error": f"Agent '{agent_id}' not found", "status": "NOT_FOUND"},
                ["Agent not found"],
            )

        worker = self.spawner.spawn(agent)
        task_msg = StructuredTaskMessage(
            task_id=f"del_{agent.id}",
            objective=task_text,
            target_agent_id=agent.id,
            deliverable=deliverable,
            constraints=TaskConstraints(do_not_modify_production=no_prod),
        )

        try:
            result = await self.executor.execute(worker, task_msg)
            await self.registry.record_task_outcome(
                agent_id=agent.id,
                success=True,
                confidence=result.confidence,
                cost=float(result.cost_units),
                latency_ms=result.latency_ms,
            )

            return ToolResult(
                {
                    "status": result.status.value,
                    "agent": agent.name,
                    "role": agent.role,
                    "summary": result.summary,
                    "findings": result.findings,
                    "recommendations": result.recommended_actions,
                    "evidence": result.evidence,
                    "confidence": result.confidence,
                },
                result.evidence,
            )
        finally:
            self.spawner.terminate(worker.instance_id)


# ── 5. agent.spawn_team ────────────────────────────────────────────────────────


class AgentSpawnTeamTool:
    """Tool allowing CEO to dynamically assemble and execute a coordinated multi-agent team."""

    def __init__(
        self,
        registry: UniversalAgentRegistry | None = None,
        team_orchestrator: TeamOrchestrator | None = None,
    ) -> None:
        self.registry = registry or get_global_agent_registry()
        self.orchestrator = team_orchestrator or TeamOrchestrator(self.registry)

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agent.spawn_team",
            "Dynamically assemble a team of specialists to solve a complex multi-disciplinary objective.",
            {
                "type": "object",
                "required": ["objective"],
                "properties": {
                    "objective": {
                        "type": "string",
                        "description": "High-level cross-functional goal",
                    },
                    "max_specialists": {
                        "type": "integer",
                        "description": "Max number of specialists in team",
                        "default": 5,
                    },
                },
            },
            RiskLevel.HARMLESS_WRITE,
            source="agent_router",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        objective = str(arguments.get("objective", ""))
        max_spec_val = arguments.get("max_specialists", 5)
        max_spec = int(str(max_spec_val)) if isinstance(max_spec_val, (int, str)) else 5

        res = await self.orchestrator.assemble_and_run_team(objective, max_specialists=max_spec)
        return ToolResult(res, res.get("evidence", []))


# ── 6. agent.create ────────────────────────────────────────────────────────────


class AgentCreateTool:
    """Tool allowing CEO to dynamically create a temporary or permanent custom specialist."""

    def __init__(self, registry: UniversalAgentRegistry | None = None) -> None:
        self.registry = registry or get_global_agent_registry()

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agent.create",
            "Create a new specialist agent persona on demand when no suitable agent exists in the roster.",
            {
                "type": "object",
                "required": ["name", "role", "mission"],
                "properties": {
                    "name": {"type": "string", "description": "Display name of the specialist"},
                    "role": {"type": "string", "description": "Specific professional role"},
                    "division": {
                        "type": "string",
                        "description": "Division (engineering, marketing, sales, finance, operations, etc.)",
                        "default": "general",
                    },
                    "mission": {
                        "type": "string",
                        "description": "Core mission and specialist instructions",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tools required by this specialist",
                    },
                },
            },
            RiskLevel.HARMLESS_WRITE,
            source="agent_router",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        name = str(arguments.get("name", ""))
        role = str(arguments.get("role", ""))
        div_str = str(arguments.get("division", "general")).lower()
        mission = str(arguments.get("mission", ""))
        tools = arguments.get("tools")
        tool_list = [str(t) for t in tools] if isinstance(tools, list) else None

        division = AgentDivision.GENERAL
        try:
            division = AgentDivision(div_str)
        except ValueError:
            pass

        # Use GeneratedAgentProvider
        gen_provider = getattr(self.registry, "generated_provider", None)
        if gen_provider is None:
            # Fallback
            for p in self.registry.providers:
                if hasattr(p, "create_dynamic_agent"):
                    gen_provider = p
                    break

        if gen_provider and hasattr(gen_provider, "create_dynamic_agent"):
            agent = gen_provider.create_dynamic_agent(
                name=name,
                role=role,
                division=division,
                mission=mission,
                tools=tool_list,
            )
            return ToolResult(
                {
                    "status": "CREATED",
                    "agent_id": agent.id,
                    "name": agent.name,
                    "role": agent.role,
                    "division": agent.division.value,
                    "tools": agent.default_tools,
                },
                [f"Dynamically created specialist agent: {agent.name} ({agent.role})"],
            )

        return ToolResult(
            {"error": "GeneratedAgentProvider not available", "status": "ERROR"},
            ["Creation failed"],
        )


# ── Legacy tool for backwards compatibility ────────────────────────────────────


class DelegateResearchTool:
    def __init__(self, runtime: Any = None) -> None:
        self.runtime = runtime

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "agents.delegate.research",
            "Run a bounded, parallel research simulation through temporary workers",
            {
                "type": "object",
                "required": ["objective", "items"],
                "properties": {
                    "objective": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}, "maxItems": 100},
                    "worker_count": {"type": "integer", "minimum": 1, "maximum": 10},
                },
            },
            RiskLevel.READ,
            source="agent_runtime",
        )

    async def execute(
        self, arguments: dict[str, object], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        objective = arguments.get("objective")
        items = arguments.get("items")
        worker_count = arguments.get("worker_count", 4)
        if (
            not isinstance(objective, str)
            or not isinstance(items, list)
            or not all(isinstance(item, str) for item in items)
            or not isinstance(worker_count, int)
        ):
            raise ValueError("objective, string items, and integer worker_count are required")
        if self.runtime:
            result = await self.runtime.delegate(objective, items, worker_count=worker_count)
            return ToolResult(result, list(result["evidence"]))
        return ToolResult({"status": "success", "items": items}, [f"Researched {len(items)} items"])


def agent_tools(runtime: Any = None) -> list[Any]:
    """Expose full suite of agent router primitive tools."""
    reg = get_global_agent_registry()
    return [
        AgentSearchTool(reg),
        AgentInspectTool(reg),
        AgentSpawnTool(reg),
        AgentDelegateTool(reg),
        AgentSpawnTeamTool(reg),
        AgentCreateTool(reg),
        DelegateResearchTool(runtime),
    ]
