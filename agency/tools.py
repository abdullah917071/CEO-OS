"""Tools for Agency Agents subsystem: listing, inspection, matching, and execution."""

from __future__ import annotations

import dataclasses
from typing import Any

from agency.engine import AgencyAgentsEngine
from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult


class AgencySkillsListTool(Tool):
    """Tool to list indexed Agency Agent skills filtered by domain or tag."""

    def __init__(self, engine: AgencyAgentsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="agency.skills.list",
            description="List available Agency Agent skills and specializations",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Filter by domain"},
                    "tag": {"type": "string", "description": "Filter by tag"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:agency",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        domain = arguments.get("domain")
        tag = arguments.get("tag")
        skills = self._engine.list_skills(domain=domain, tag=tag)

        summary = [
            {
                "name": s.name,
                "role": s.role,
                "domain": s.domain.value,
                "description": s.description,
                "tags": s.tags,
            }
            for s in skills
        ]

        evidence = [
            f"Retrieved {len(skills)} Agency Agent skills"
            + (f" for domain '{domain}'" if domain else "")
            + (f" with tag '{tag}'" if tag else "")
        ]

        return ToolResult(
            output={"skills": summary, "count": len(summary)},
            evidence=evidence,
        )


class AgencySkillsGetTool(Tool):
    """Tool to inspect full persona rules and workflow phases of an Agency Agent."""

    def __init__(self, engine: AgencyAgentsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="agency.skills.get",
            description="Retrieve persona instructions, rules, and phases for an Agency Agent",
            input_schema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Agency skill name (e.g. agency-finops-engineer)",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:agency",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        name = str(arguments["name"])
        skill = self._engine.get_skill(name)
        if not skill:
            return ToolResult(
                output={"error": f"Agency skill '{name}' not found"},
                evidence=[f"Skill '{name}' lookup failed"],
            )

        n_r = len(skill.critical_rules)
        n_p = len(skill.workflow_phases)
        evidence = [
            f"Agency Persona '{skill.name}' ({skill.role})",
            f"Domain: {skill.domain.value}, Rules: {n_r}, Phases: {n_p}",
        ]

        return ToolResult(
            output=dataclasses.asdict(skill),
            evidence=evidence,
        )


class AgencySkillsMatchTool(Tool):
    """Tool to automatically match a user prompt or task against all Agency Agent skills."""

    def __init__(self, engine: AgencyAgentsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="agency.skills.match",
            description="Match task intent to optimal Agency Agent persona with relevance scoring",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Task description or prompt to match",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 3,
                        "description": "Number of top matches",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:agency",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        query = str(arguments["query"])
        top_k = int(arguments.get("top_k", 3))

        match_res = self._engine.match_skill(query, top_k=top_k)

        if match_res.best_match:
            bm = match_res.best_match
            best_desc = f"Best match: '{bm.skill_name}' (Score: {bm.relevance_score})"
        else:
            best_desc = "No match found"

        evidence = [
            f"Evaluated {match_res.total_skills_evaluated} Agency skills for query: '{query}'",
            best_desc,
        ]

        return ToolResult(
            output=dataclasses.asdict(match_res),
            evidence=evidence,
        )


class AgencyAgentSpawnTool(Tool):
    """Tool to dynamically synthesize and register an AgentTemplate from an Agency Agent skill."""

    def __init__(self, engine: AgencyAgentsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="agency.agent.spawn",
            description="Synthesize an agent template configured with an Agency Agent persona",
            input_schema={
                "type": "object",
                "required": ["skill_name"],
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Agency skill name to instantiate",
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Optional custom instance name",
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:agency",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        skill_name = str(arguments["skill_name"])
        agent_name = arguments.get("agent_name", skill_name)

        try:
            template = self._engine.synthesize_agent_template(skill_name)
            evidence = [
                f"Synthesized Agent Template '{template.name}' ({template.role})",
                f"Model: {template.model_class}, Caps: {len(template.allowed_capabilities)}",
            ]
            return ToolResult(
                output={
                    "agent_name": agent_name,
                    "template_name": template.name,
                    "role": template.role,
                    "model_class": template.model_class,
                    "allowed_capabilities": list(template.allowed_capabilities),
                    "budget": dataclasses.asdict(template.budget),
                },
                evidence=evidence,
            )
        except Exception as exc:
            return ToolResult(
                output={"error": str(exc)},
                evidence=[f"Failed to synthesize agent template: {exc}"],
            )


class AgencyTaskExecuteTool(Tool):
    """Tool to execute a task guided by an Agency Agent's domain rules and quality gates."""

    def __init__(self, engine: AgencyAgentsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="agency.task.execute",
            description="Execute a task with Agency Agent persona guidance and quality gates",
            input_schema={
                "type": "object",
                "required": ["task_id", "objective"],
                "properties": {
                    "task_id": {"type": "string", "description": "Unique task identifier"},
                    "objective": {"type": "string", "description": "Task objective to accomplish"},
                    "skill_name": {
                        "type": "string",
                        "description": "Optional explicit agency skill to use",
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional task context parameters",
                    },
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:agency",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        task_id = str(arguments["task_id"])
        objective = str(arguments["objective"])
        skill_name = arguments.get("skill_name")
        context = arguments.get("context")

        result = self._engine.execute_with_skill(
            task_id=task_id,
            objective=objective,
            skill_name=skill_name,
            context=context,
        )

        return ToolResult(
            output=dataclasses.asdict(result),
            evidence=result.evidence,
        )
