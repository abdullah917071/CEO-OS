"""Automated import smoke test suite for all CEO-OS production packages and modules."""

from __future__ import annotations

import importlib

import pytest

PRODUCTION_PACKAGES = [
    "apps.api.src.ceo_os_api",
    "core",
    "agents",
    "tools",
    "integrations",
    "intelligence",
    "memory",
    "computer",
    "browser",
    "vision",
    "voice",
    "communications",
    "skills",
    "ceo_agent",
    "jarvis",
    "hermes",
    "gstack",
    "agency",
    "proactive",
    "production",
    "workflows",
]


@pytest.mark.parametrize("package_name", PRODUCTION_PACKAGES)
def test_production_package_import(package_name: str) -> None:
    """Verify that every top-level runtime package imports cleanly without errors."""
    mod = importlib.import_module(package_name)
    assert mod is not None


def test_ceo_agent_subsystem_imports() -> None:
    """Verify CEO Agent runtime components."""
    from ceo_agent.agent import CeoAIAgent
    from ceo_agent.contracts import CeoRunResult, CeoRunStatus
    from ceo_agent.parser import CeoToolParser
    from ceo_agent.sanitizer import create_safe_execution_summary, sanitize_thought_text
    from ceo_agent.serialization import safe_json_dumps, safe_json_serialize

    assert CeoAIAgent is not None
    assert CeoRunStatus.SUCCESS.value == "SUCCESS"
    assert CeoRunResult is not None
    assert CeoToolParser is not None
    assert callable(create_safe_execution_summary)
    assert callable(sanitize_thought_text)
    assert callable(safe_json_dumps)
    assert callable(safe_json_serialize)


def test_jarvis_subsystem_imports() -> None:
    """Verify Jarvis voice assistant and backend tools."""
    from jarvis.backend.audio.capture import AudioCaptureStream
    from jarvis.backend.audio.devices import list_audio_devices
    from jarvis.backend.config.database import JarvisDatabase
    from jarvis.backend.config.secrets import JarvisSecretsManager
    from jarvis.backend.gemini.auth import GeminiAuthManager
    from jarvis.backend.gemini.live import GeminiLiveSocket
    from jarvis.backend.tools.permissions import ToolPermissionManager
    from jarvis.backend.tools.registry import JarvisToolRegistry
    from jarvis.backend.wakeword.detector import LocalWakeWordDetector

    assert AudioCaptureStream is not None
    assert callable(list_audio_devices)
    assert JarvisDatabase is not None
    assert JarvisSecretsManager is not None
    assert GeminiAuthManager is not None
    assert GeminiLiveSocket is not None
    assert ToolPermissionManager is not None
    assert JarvisToolRegistry is not None
    assert LocalWakeWordDetector is not None


def test_agency_and_router_subsystem_imports() -> None:
    """Verify Agency dynamic router and agent catalog."""
    from agency.catalog import AgencyCatalog
    from agency.contracts import AgencySkillPersona
    from agency.engine import AgencyAgentsEngine
    from agency.matcher import AgencySkillMatcher
    from agency.tools import AgencyAgentSpawnTool, AgencySkillsListTool
    from agents.registry import (
        AgencyAgentProvider,
        AgentDefinition,
        AgentRanker,
        AgentRouter,
        GeneratedAgentProvider,
        NativeAgentProvider,
        UniversalAgentRegistry,
    )
    from agents.tools import (
        AgentCreateTool,
        AgentDelegateTool,
        AgentInspectTool,
        AgentSearchTool,
        AgentSpawnTeamTool,
        AgentSpawnTool,
    )

    assert AgencyCatalog is not None
    assert AgencySkillPersona is not None
    assert AgencyAgentsEngine is not None
    assert AgencySkillMatcher is not None
    assert AgencySkillsListTool is not None
    assert AgencyAgentSpawnTool is not None
    assert AgencyAgentProvider is not None
    assert AgentDefinition is not None
    assert AgentRanker is not None
    assert AgentRouter is not None
    assert GeneratedAgentProvider is not None
    assert NativeAgentProvider is not None
    assert UniversalAgentRegistry is not None
    assert AgentSearchTool is not None
    assert AgentInspectTool is not None
    assert AgentSpawnTool is not None
    assert AgentDelegateTool is not None
    assert AgentSpawnTeamTool is not None
    assert AgentCreateTool is not None


def test_hermes_subsystem_imports() -> None:
    """Verify Hermes trajectory and tool interfaces."""
    from hermes.contracts import HermesTrajectoryRecord
    from hermes.llm import DeterministicHermesEngine, OpenAiCompatibleHermesEngine
    from hermes.tools import (
        HermesAgentRunTool,
        HermesReflectSynthesizeTool,
        HermesTrajectoryExportTool,
    )
    from hermes.trajectory import HermesTrajectoryStore

    assert HermesTrajectoryRecord is not None
    assert DeterministicHermesEngine is not None
    assert OpenAiCompatibleHermesEngine is not None
    assert HermesAgentRunTool is not None
    assert HermesReflectSynthesizeTool is not None
    assert HermesTrajectoryExportTool is not None
    assert HermesTrajectoryStore is not None


def test_core_and_workflows_imports() -> None:
    """Verify core contracts and workflow engines."""
    from core.contracts import (
        CapabilitySpec,
        ExecutionPlan,
        PlanStep,
        RiskLevel,
        RuntimeEvent,
        TaskControl,
        TaskStatus,
        ToolResult,
    )
    from skills.engine import SkillsEngine
    from workflows import ReservationRequest, ReservationResult, RestaurantBookingWorkflow

    assert CapabilitySpec is not None
    assert ExecutionPlan is not None
    assert PlanStep is not None
    assert RiskLevel is not None
    assert RuntimeEvent is not None
    assert TaskControl is not None
    assert TaskStatus is not None
    assert ToolResult is not None
    assert SkillsEngine is not None
    assert ReservationRequest is not None
    assert ReservationResult is not None
    assert RestaurantBookingWorkflow is not None
