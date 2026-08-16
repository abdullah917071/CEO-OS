"""Capability tools for creating, executing, testing, versioning, and managing skills."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from skills.contracts import SkillStep
from skills.engine import SkillsEngine


class SkillCreateTool:
    """Tool to register a new procedural skill."""

    def __init__(self, engine: SkillsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="skills.create",
            description="Create and register a new reusable procedural skill from workflow steps",
            input_schema={
                "type": "object",
                "required": ["name", "description", "steps"],
                "properties": {
                    "name": {"type": "string", "description": "Human readable name"},
                    "description": {"type": "string", "description": "Skill summary"},
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["step_id", "capability", "arguments_template"],
                            "properties": {
                                "step_id": {"type": "string"},
                                "capability": {"type": "string"},
                                "arguments_template": {"type": "object"},
                                "success_condition": {"type": "string"},
                                "timeout_seconds": {"type": "number", "default": 30.0},
                            },
                        },
                    },
                    "parameters_schema": {"type": "object", "default": {}},
                    "category": {"type": "string", "default": "general"},
                    "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                    "owner_agent": {"type": "string", "default": "ceo"},
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:skills",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        name = str(arguments["name"])
        desc = str(arguments["description"])
        raw_steps = arguments.get("steps", [])
        steps = [
            SkillStep(
                step_id=s["step_id"],
                capability=s["capability"],
                arguments_template=s.get("arguments_template", {}),
                success_condition=s.get("success_condition", "Step completed"),
                timeout_seconds=float(s.get("timeout_seconds", 30.0)),
            )
            for s in raw_steps
        ]
        param_schema = arguments.get("parameters_schema")
        category = str(arguments.get("category", "general"))
        tags = list(arguments.get("tags", []))
        owner = str(arguments.get("owner_agent", "ceo"))

        skill = self._engine.create_skill(
            name=name,
            description=desc,
            steps=steps,
            parameters_schema=param_schema,
            category=category,
            tags=tags,
            owner_agent=owner,
        )

        return ToolResult(
            output=dataclasses.asdict(skill),
            evidence=[
                f"Created skill '{skill.name}' (ID: {skill.skill_id}, v{skill.version}) "
                f"with {len(skill.steps)} procedural steps"
            ],
        )


class SkillExecuteTool:
    """Tool to execute a registered procedural skill."""

    def __init__(
        self,
        engine: SkillsEngine,
        registry_getter: Any = None,
    ) -> None:
        self._engine = engine
        self._registry_getter = registry_getter

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="skills.execute",
            description="Execute a learned procedural skill with parameter inputs",
            input_schema={
                "type": "object",
                "required": ["skill_id"],
                "properties": {
                    "skill_id": {"type": "string", "description": "ID of skill to execute"},
                    "inputs": {
                        "type": "object",
                        "description": "Parameters for execution",
                        "default": {},
                    },
                },
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:skills",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        skill_id = str(arguments["skill_id"])
        inputs = arguments.get("inputs", {})
        reg = self._registry_getter() if callable(self._registry_getter) else None

        result = await self._engine.execute_skill(
            skill_id=skill_id, inputs=inputs, capability_registry=reg
        )

        return ToolResult(
            output=dataclasses.asdict(result),
            evidence=[
                f"Skill '{skill_id}' execution {result.status} "
                f"({result.steps_executed}/{result.total_steps} steps in {result.duration_ms}ms)"
            ]
            + result.evidence,
        )


class SkillTestTool:
    """Tool to dry-run and simulate a procedural skill."""

    def __init__(
        self,
        engine: SkillsEngine,
        registry_getter: Any = None,
    ) -> None:
        self._engine = engine
        self._registry_getter = registry_getter

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="skills.test",
            description="Dry-run test and validate a skill with mock inputs and step verification",
            input_schema={
                "type": "object",
                "required": ["skill_id"],
                "properties": {
                    "skill_id": {"type": "string", "description": "ID of skill to test"},
                    "mock_inputs": {
                        "type": "object",
                        "description": "Mock parameters",
                        "default": {},
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:skills",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        skill_id = str(arguments["skill_id"])
        mock_inputs = arguments.get("mock_inputs", {})
        reg = self._registry_getter() if callable(self._registry_getter) else None

        test_res = self._engine.test_skill(
            skill_id=skill_id,
            mock_inputs=mock_inputs,
            capability_registry=reg,
        )

        return ToolResult(
            output=dataclasses.asdict(test_res),
            evidence=[
                f"Skill '{skill_id}' test {'PASSED' if test_res.passed else 'FAILED'} "
                f"with {len(test_res.validation_errors)} error(s)"
            ],
        )


class SkillVersionTool:
    """Tool to bump version and record changelog for a skill."""

    def __init__(self, engine: SkillsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="skills.version",
            description="Create a new version bump for a skill with changelog",
            input_schema={
                "type": "object",
                "required": ["skill_id", "new_version", "changelog"],
                "properties": {
                    "skill_id": {"type": "string"},
                    "new_version": {"type": "string", "description": "Semantic version e.g. 1.1.0"},
                    "changelog": {"type": "string", "description": "Description of improvements"},
                    "new_description": {"type": "string"},
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:skills",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        skill_id = str(arguments["skill_id"])
        new_version = str(arguments["new_version"])
        changelog = str(arguments["changelog"])
        new_desc = arguments.get("new_description")

        updated = self._engine.version_skill(
            skill_id=skill_id,
            new_version=new_version,
            changelog=changelog,
            new_description=new_desc,
        )

        return ToolResult(
            output=dataclasses.asdict(updated),
            evidence=[f"Skill '{skill_id}' updated to v{updated.version} (Changelog: {changelog})"],
        )


class SkillDisableTool:
    """Tool to enable or disable a procedural skill."""

    def __init__(self, engine: SkillsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="skills.disable",
            description="Enable or disable a procedural skill",
            input_schema={
                "type": "object",
                "required": ["skill_id"],
                "properties": {
                    "skill_id": {"type": "string"},
                    "disabled": {"type": "boolean", "default": True},
                },
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:skills",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        skill_id = str(arguments["skill_id"])
        disabled = bool(arguments.get("disabled", True))
        skill = self._engine.disable_skill(skill_id=skill_id, disabled=disabled)
        state_str = "disabled" if disabled else "enabled"

        return ToolResult(
            output=dataclasses.asdict(skill),
            evidence=[f"Skill '{skill_id}' has been {state_str}"],
        )


class SkillListTool:
    """Tool to list available procedural skills."""

    def __init__(self, engine: SkillsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="skills.list",
            description="List available procedural skills filtered by category or owner",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "enabled_only": {"type": "boolean", "default": False},
                },
            },
            risk=RiskLevel.READ,
            source="integration:skills",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        cat = arguments.get("category")
        enabled = bool(arguments.get("enabled_only", False))
        skills = self._engine.list_skills(category=cat, enabled_only=enabled)

        return ToolResult(
            output=[dataclasses.asdict(s) for s in skills],
            evidence=[f"Found {len(skills)} skill(s) in library"],
        )


class SkillGetTool:
    """Tool to inspect detailed procedural skill definition."""

    def __init__(self, engine: SkillsEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="skills.get",
            description="Inspect detailed definition and step sequence of a skill",
            input_schema={
                "type": "object",
                "required": ["skill_id"],
                "properties": {"skill_id": {"type": "string"}},
            },
            risk=RiskLevel.READ,
            source="integration:skills",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        skill_id = str(arguments["skill_id"])
        skill = self._engine.get_skill(skill_id)

        return ToolResult(
            output=dataclasses.asdict(skill),
            evidence=[
                f"Skill '{skill.name}' (v{skill.version}, {skill.category}) "
                f"has {len(skill.steps)} steps and {skill.stats.runs_count} run(s)"
            ],
        )
