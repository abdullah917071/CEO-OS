"""CEO OS Executive AI Agent: drives multi-turn ReAct reasoning and tool execution."""

from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from ceo_agent.contracts import (
    CeoMessage,
    CeoRole,
    CeoRunResult,
    CeoToolCall,
    CeoToolResponse,
    CeoTrajectoryRecord,
    CeoTrajectoryStep,
)
from ceo_agent.llm import CeoLlmProtocol, DeterministicCeoEngine
from ceo_agent.parser import CeoToolParser
from ceo_agent.prompting import CeoPromptFormatter
from ceo_agent.reflection import CeoReflectiveEngine
from ceo_agent.swarm import CeoSubagentSwarm
from ceo_agent.trajectory import CeoTrajectoryStore
from core.capabilities import CapabilityRegistry
from core.contracts import CapabilitySpec

logger = logging.getLogger(__name__)


class CeoAIAgent:
    """Core autonomous executive agent engine implementing the CEO OS ReAct reasoning loop."""

    def __init__(
        self,
        capabilities: CapabilityRegistry | None = None,
        llm: CeoLlmProtocol | None = None,
        trajectory_store: CeoTrajectoryStore | None = None,
        reflective_engine: CeoReflectiveEngine | None = None,
        prompt_formatter: CeoPromptFormatter | None = None,
    ) -> None:
        self.capabilities = capabilities
        self.llm: CeoLlmProtocol = llm or DeterministicCeoEngine()
        self.trajectory_store = trajectory_store or CeoTrajectoryStore()
        self.reflective_engine = reflective_engine or CeoReflectiveEngine(llm=self.llm)
        self.prompt_formatter = prompt_formatter or CeoPromptFormatter()
        self.swarm = CeoSubagentSwarm(self)

    def _get_available_capabilities(self) -> list[CapabilitySpec]:
        if not self.capabilities:
            return []
        return self.capabilities.list()

    async def run(
        self,
        task_id: str,
        objective: str,
        *,
        max_turns: int = 6,
    ) -> CeoRunResult:
        """Execute an autonomous CEO OS multi-turn ReAct reasoning loop."""
        start_time = time.monotonic()
        trajectory_id = f"traj_{uuid4().hex[:8]}"

        available_caps = self._get_available_capabilities()
        system_prompt = self.prompt_formatter.format_system_prompt(available_caps)

        messages: list[CeoMessage] = [
            CeoMessage(role=CeoRole.SYSTEM, content=system_prompt),
            CeoMessage(role=CeoRole.USER, content=objective),
        ]

        steps: list[CeoTrajectoryStep] = []
        all_evidence: list[str] = []
        final_answer = ""
        last_thought = ""

        for turn in range(1, max_turns + 1):
            turn_start = time.monotonic()
            model_output = await self.llm.generate(messages)

            thought = CeoToolParser.extract_thought(model_output)
            tool_calls = CeoToolParser.extract_tool_calls(model_output)
            clean_text = CeoToolParser.clean_final_answer(model_output)

            if thought:
                last_thought = thought

            if not tool_calls:
                final_answer = clean_text or model_output
                turn_dur = (time.monotonic() - turn_start) * 1000.0
                steps.append(
                    CeoTrajectoryStep(
                        step_index=turn,
                        thought=thought or "Executive synthesis formulated.",
                        tool_call=None,
                        tool_response=None,
                        duration_ms=turn_dur,
                    )
                )
                break

            for call in tool_calls:
                tool_start = time.monotonic()
                tool_resp = await self._execute_tool(call)
                tool_dur = (time.monotonic() - tool_start) * 1000.0

                if tool_resp.evidence:
                    all_evidence.extend(tool_resp.evidence)

                steps.append(
                    CeoTrajectoryStep(
                        step_index=turn,
                        thought=thought,
                        tool_call=call,
                        tool_response=tool_resp,
                        duration_ms=tool_dur,
                    )
                )

                call_json = json.dumps({"name": call.name, "arguments": call.arguments})
                messages.append(
                    CeoMessage(
                        role=CeoRole.ASSISTANT,
                        content=f"<thought>\n{thought}\n</thought>\n<tool_call>\n{call_json}\n</tool_call>",
                        thought=thought,
                        tool_calls=[call],
                    )
                )

                resp_json = json.dumps(tool_resp.output)
                messages.append(
                    CeoMessage(
                        role=CeoRole.TOOL,
                        content=f"<tool_response>\n{resp_json}\n</tool_response>",
                        tool_response=tool_resp,
                    )
                )

        total_duration_ms = (time.monotonic() - start_time) * 1000.0

        if not final_answer and steps:
            final_answer = f"Autonomous CEO OS execution completed for: '{objective}'."

        record = CeoTrajectoryRecord(
            trajectory_id=trajectory_id,
            task_id=task_id,
            objective=objective,
            system_prompt=system_prompt,
            steps=steps,
            final_response=final_answer,
            total_duration_ms=total_duration_ms,
            status="SUCCESS",
        )
        self.trajectory_store.save(record)

        reflection = await self.reflective_engine.reflect(record)

        return CeoRunResult(
            run_id=f"run_{uuid4().hex[:8]}",
            task_id=task_id,
            objective=objective,
            status="SUCCESS",
            thought=last_thought,
            final_answer=final_answer,
            trajectory=record,
            reflection=reflection,
            evidence=all_evidence,
            duration_ms=total_duration_ms,
        )

    async def _execute_tool(self, call: CeoToolCall) -> CeoToolResponse:
        """Execute tool through Capability Registry or fallback to Jarvis tool runner."""
        # 1. Try CapabilityRegistry first
        if self.capabilities and self.capabilities.has(call.name):
            try:
                tool = self.capabilities.get(call.name)
                if tool is not None:
                    result = await tool.execute(call.arguments)
                    return CeoToolResponse(
                        name=call.name,
                        output=result.output,
                        evidence=result.evidence,
                        call_id=call.call_id,
                    )
            except Exception as exc:
                logger.exception("Error executing tool %s via capability registry", call.name)
                return CeoToolResponse(
                    name=call.name,
                    output={"error": str(exc)},
                    evidence=[f"Tool `{call.name}` failed with error: {exc}"],
                    error=str(exc),
                    call_id=call.call_id,
                )

        # 2. Try native Jarvis / macOS / browser tool execution
        try:
            from jarvis.backend.tools.permissions import ToolPermissionManager
            from jarvis.backend.tools.registry import JarvisToolRegistry

            jarvis_registry = JarvisToolRegistry(ToolPermissionManager())
            # Normalize name by removing namespace prefixes
            clean_name = (
                call.name.replace("browser.", "").replace("macos.", "").replace("media.", "")
            )
            if clean_name in jarvis_registry._tools:
                jarvis_res = await jarvis_registry.execute_tool(clean_name, call.arguments)
                return CeoToolResponse(
                    name=call.name,
                    output=jarvis_res,
                    evidence=[f"Executed macOS/browser tool `{clean_name}`: {jarvis_res}"],
                    call_id=call.call_id,
                )
        except Exception as exc:
            logger.warning("Jarvis tool execution fallback skipped or failed: %s", exc)

        logger.warning("Tool %s not found in capability registry", call.name)
        return CeoToolResponse(
            name=call.name,
            output={"status": "executed", "arguments": call.arguments},
            evidence=[f"Simulated execution of `{call.name}`"],
            call_id=call.call_id,
        )


# Backwards compatibility alias
HermesAIAgent = CeoAIAgent
