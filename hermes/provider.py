"""Hermes & OpenRouter Model Providers: integrates reasoning engines into ModelRouter."""

from __future__ import annotations

from core.contracts import CapabilitySpec, ExecutionPlan, ModelProvider, PlanStep
from hermes.agent import HermesAIAgent
from hermes.llm import DeterministicHermesEngine, HermesLlmProtocol, OpenAiCompatibleHermesEngine


class HermesModelProvider(ModelProvider):
    """Model provider powered by the Nous Hermes reasoning engine."""

    def __init__(self, llm: HermesLlmProtocol | None = None) -> None:
        self._llm = llm or DeterministicHermesEngine()

    @property
    def name(self) -> str:
        return "hermes"

    async def plan(self, message: str, capabilities: list[CapabilitySpec]) -> ExecutionPlan:
        """Formulate execution plan using Hermes scratchpad reasoning."""
        available_names = {c.name for c in capabilities}
        steps: list[PlanStep] = []

        # Create temporary agent to generate initial reasoning and tool calls
        agent = HermesAIAgent(llm=self._llm)
        run_res = await agent.run(task_id="planner_task", objective=message)

        for step in run_res.trajectory.steps:
            if step.tool_call and step.tool_call.name in available_names:
                steps.append(
                    PlanStep(
                        capability=step.tool_call.name,
                        arguments=step.tool_call.arguments,
                        success_condition=(
                            f"Capability `{step.tool_call.name}` executed with verified evidence"
                        ),
                    )
                )

        if not steps:
            # Fallback direct execution step
            steps.append(
                PlanStep(
                    capability="time.now",
                    arguments={},
                    success_condition="Directive acknowledged by Hermes reasoning engine",
                )
            )

        return ExecutionPlan(
            objective=message.strip(),
            success_conditions=[s.success_condition for s in steps],
            steps=steps,
        )


class OpenRouterModelProvider(ModelProvider):
    """Model provider connecting to OpenRouter API (e.g. nvidia/nemotron-3.5-lightning:free)."""

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "nvidia/nemotron-3.5-lightning:free",
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        if api_key:
            self._engine: HermesLlmProtocol = OpenAiCompatibleHermesEngine(
                base_url=base_url,
                api_key=api_key,
                model_name=model_name,
            )
        else:
            self._engine = DeterministicHermesEngine()

    @property
    def name(self) -> str:
        return "openrouter"

    async def plan(self, message: str, capabilities: list[CapabilitySpec]) -> ExecutionPlan:
        """Formulate execution plan using OpenRouter model."""
        agent = HermesAIAgent(llm=self._engine)
        run_res = await agent.run(task_id="openrouter_planner", objective=message)
        available_names = {c.name for c in capabilities}
        steps: list[PlanStep] = []

        for step in run_res.trajectory.steps:
            if step.tool_call and step.tool_call.name in available_names:
                steps.append(
                    PlanStep(
                        capability=step.tool_call.name,
                        arguments=step.tool_call.arguments,
                        success_condition=(
                            f"Capability `{step.tool_call.name}` executed with verified evidence"
                        ),
                    )
                )

        if not steps:
            steps.append(
                PlanStep(
                    capability="time.now",
                    arguments={},
                    success_condition="Directive processed by OpenRouter model",
                )
            )

        return ExecutionPlan(
            objective=message.strip(),
            success_conditions=[s.success_condition for s in steps],
            steps=steps,
        )
