"""Hermes Autonomous AI Agent: drives the multi-turn ReAct reasoning loop."""

from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from core.capabilities import CapabilityRegistry
from core.contracts import CapabilitySpec
from hermes.contracts import (
    HermesMessage,
    HermesRole,
    HermesRunResult,
    HermesToolCall,
    HermesToolResponse,
    HermesTrajectoryRecord,
    HermesTrajectoryStep,
)
from hermes.llm import DeterministicHermesEngine, HermesLlmProtocol
from hermes.parser import HermesToolParser
from hermes.prompting import HermesPromptFormatter
from hermes.reflection import HermesReflectiveEngine
from hermes.swarm import HermesSubagentSwarm
from hermes.trajectory import HermesTrajectoryStore

logger = logging.getLogger(__name__)


class HermesAIAgent:
    """Core autonomous agent engine implementing the Nous Hermes reasoning loop."""

    def __init__(
        self,
        capabilities: CapabilityRegistry | None = None,
        llm: HermesLlmProtocol | None = None,
        trajectory_store: HermesTrajectoryStore | None = None,
        reflective_engine: HermesReflectiveEngine | None = None,
        swarm: HermesSubagentSwarm | None = None,
    ) -> None:
        self.capabilities = capabilities
        self.llm: HermesLlmProtocol = llm or DeterministicHermesEngine()
        self.trajectory_store = trajectory_store or HermesTrajectoryStore()
        self.reflective_engine = reflective_engine or HermesReflectiveEngine()
        self.swarm = swarm or HermesSubagentSwarm(capabilities)

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
        memory_context: list[str] | None = None,
        rules: list[str] | None = None,
    ) -> HermesRunResult:
        """Execute an autonomous Hermes multi-turn ReAct reasoning loop."""
        start_time = time.monotonic()
        trajectory_id = f"traj_{uuid4().hex[:8]}"

        available_caps = self._get_available_capabilities()
        system_prompt = HermesPromptFormatter.build_system_prompt(
            available_caps,
            memory_context=memory_context,
            rules=rules,
        )

        messages: list[HermesMessage] = [
            HermesMessage(role=HermesRole.SYSTEM, content=system_prompt),
            HermesMessage(role=HermesRole.USER, content=objective),
        ]

        steps: list[HermesTrajectoryStep] = []
        all_evidence: list[str] = []
        final_answer = ""
        last_thought = ""

        for turn in range(1, max_turns + 1):
            turn_start = time.monotonic()
            model_output = await self.llm.generate(messages)

            thought = HermesToolParser.extract_thought(model_output)
            tool_calls = HermesToolParser.extract_tool_calls(model_output)
            clean_text = HermesToolParser.strip_tool_tags(model_output)

            if thought:
                last_thought = thought

            if not tool_calls:
                final_answer = clean_text or model_output
                turn_dur = (time.monotonic() - turn_start) * 1000.0
                steps.append(
                    HermesTrajectoryStep(
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
                    HermesTrajectoryStep(
                        step_index=turn,
                        thought=thought,
                        tool_call=call,
                        tool_response=tool_resp,
                        duration_ms=tool_dur,
                    )
                )

                call_json = json.dumps({"name": call.name, "arguments": call.arguments})
                messages.append(
                    HermesMessage(
                        role=HermesRole.ASSISTANT,
                        content=f"<thought>\n{thought}\n</thought>\n<tool_call>\n{call_json}\n</tool_call>",
                        thought=thought,
                        tool_calls=[call],
                    )
                )

                resp_json = json.dumps(tool_resp.output)
                messages.append(
                    HermesMessage(
                        role=HermesRole.TOOL,
                        content=f"<tool_response>\n{resp_json}\n</tool_response>",
                        tool_response=tool_resp,
                    )
                )

        total_duration_ms = (time.monotonic() - start_time) * 1000.0

        if not final_answer and steps:
            final_answer = f"Autonomous Hermes execution completed for: '{objective}'."

        record = HermesTrajectoryRecord(
            trajectory_id=trajectory_id,
            task_id=task_id,
            objective=objective,
            system_prompt=system_prompt,
            steps=steps,
            final_response=final_answer,
            total_duration_ms=total_duration_ms,
            status="SUCCESS",
        )
        self.trajectory_store.record(record)

        reflection = self.reflective_engine.reflect(record)

        return HermesRunResult(
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

    async def _execute_tool(self, call: HermesToolCall) -> HermesToolResponse:
        """Execute tool through the Capability Registry."""
        if not self.capabilities or not self.capabilities.has(call.name):
            logger.warning("Tool %s not found in capability registry", call.name)
            return HermesToolResponse(
                name=call.name,
                output={"status": "executed", "arguments": call.arguments},
                evidence=[f"Simulated execution of `{call.name}`"],
                call_id=call.call_id,
            )

        try:
            tool = self.capabilities.get(call.name)
            if tool is None:
                raise ValueError(f"Tool {call.name} returned None from registry")
            result = await tool.execute(call.arguments)
            return HermesToolResponse(
                name=call.name,
                output=result.output,
                evidence=result.evidence,
                call_id=call.call_id,
            )
        except Exception as exc:
            logger.exception("Error executing tool %s", call.name)
            return HermesToolResponse(
                name=call.name,
                output={"error": str(exc)},
                evidence=[f"Tool `{call.name}` failed with error: {exc}"],
                error=str(exc),
                call_id=call.call_id,
            )
