from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from production.engine import ProductionHardeningEngine


class ProductionSecurityAuditTool(Tool):
    """Tool to perform security audits on capabilities, secrets, and risk ceilings."""

    def __init__(self, engine: ProductionHardeningEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="production.security.audit",
            description="Audit capability permissions, credential isolation, and security posture",
            input_schema={
                "type": "object",
                "properties": {
                    "active_secret_refs": {
                        "type": "integer",
                        "description": "Number of active secret vault references",
                        "default": 4,
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:production_hardening",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        secret_refs = int(arguments.get("active_secret_refs", 4))
        report = self._engine.audit_security(active_secret_refs=secret_refs)

        c_aud = report.total_capabilities_audited
        evidence = [
            f"Security Audit Status: {report.status} (Score: {report.security_score}/100)",
            f"Audited {c_aud} capabilities: {report.read_only_count} R0, "
            f"{report.harmless_write_count} R1, {report.sensitive_business_count} R2, "
            f"{report.privileged_count} R3/R4",
            f"Secret vault references: {report.secret_references_active}, "
            f"Credential leases valid: {report.credential_leases_valid}",
        ]
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=evidence,
        )


class ProductionCostOverviewTool(Tool):
    """Tool to retrieve granular FinOps cost breakdown and unit economics."""

    def __init__(self, engine: ProductionHardeningEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="production.cost.overview",
            description="Retrieve FinOps cost breakdown across models, voice, and agents",
            input_schema={"type": "object"},
            risk=RiskLevel.READ,
            source="integration:production_hardening",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        report = self._engine.get_cost_overview()

        evidence = [
            f"Total spend: ₹{report.total_spend_inr:,.2f} ({report.tasks_processed_count} tasks)",
            f"Unit cost per task: ₹{report.unit_cost_per_task_inr:,.2f}",
        ]
        for cat, amt in report.breakdown_by_category.items():
            evidence.append(f"Spend in {cat}: ₹{amt:,.2f}")

        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=evidence,
        )


class ProductionAgentPerformanceTool(Tool):
    """Tool to inspect agent reliability, success rates, and latency profiles."""

    def __init__(self, engine: ProductionHardeningEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="production.agent.performance",
            description="Inspect agent fleet reliability, success rates, and latency",
            input_schema={"type": "object"},
            risk=RiskLevel.READ,
            source="integration:production_hardening",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        report = self._engine.get_agent_performance()

        f_rate = report.average_fleet_success_rate
        f_lat = report.average_fleet_latency_ms
        evidence = [
            f"Fleet reliability: {f_rate:.1f}% success rate across {report.fleet_size} agents",
            f"Average fleet latency: {f_lat:.0f} ms ({report.total_tasks_completed} done)",
        ]
        for m in report.agent_metrics:
            evidence.append(
                f"{m.name} [{m.domain}]: {m.success_rate_percentage:.1f}% success "
                f"({m.tasks_completed} done), avg {m.average_runtime_ms:.0f} ms"
            )

        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=evidence,
        )


class ProductionConfidenceVerifyTool(Tool):
    """Tool to evaluate task execution confidence and verify whether safety gates are needed."""

    def __init__(self, engine: ProductionHardeningEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="production.confidence.verify",
            description="Evaluate confidence score and apply safety gates for high-risk actions",
            input_schema={
                "type": "object",
                "required": ["task_id", "capability", "risk_level", "confidence_score"],
                "properties": {
                    "task_id": {"type": "string", "description": "Unique task identifier"},
                    "capability": {"type": "string", "description": "Target capability to execute"},
                    "risk_level": {
                        "type": "string",
                        "enum": ["r0", "r1", "r2", "r3", "r4"],
                        "description": "Capability risk tier",
                    },
                    "confidence_score": {
                        "type": "number",
                        "description": "Agent confidence (0.0 to 1.0)",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Supporting execution evidence",
                    },
                    "uncertainty_factors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Identified sources of uncertainty",
                    },
                },
            },
            risk=RiskLevel.READ,
            source="integration:production_hardening",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        result = self._engine.verify_confidence(
            task_id=str(arguments["task_id"]),
            capability=str(arguments["capability"]),
            risk_level=str(arguments["risk_level"]),
            confidence_score=float(arguments["confidence_score"]),
            evidence=arguments.get("evidence"),
            uncertainty_factors=arguments.get("uncertainty_factors"),
        )

        return ToolResult(
            output=dataclasses.asdict(result),
            evidence=[
                f"Confidence Verification Gate: {result.gate.value.upper()}",
                f"Rationale: {result.rationale}",
                f"Requires Human Approval: {result.requires_human_approval}",
            ],
        )


class ProductionResilienceHealthTool(Tool):
    """Tool to check operational resilience, rate limits, and recovery readiness."""

    def __init__(self, engine: ProductionHardeningEngine) -> None:
        self._engine = engine

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="production.resilience.health",
            description="Check resilience, rate limits, circuit breakers, and recovery health",
            input_schema={"type": "object"},
            risk=RiskLevel.READ,
            source="integration:production_hardening",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments, idempotency_key
        report = self._engine.get_resilience_health()

        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[
                f"Recovery Readiness Score: {report.recovery_readiness_score}/100",
                f"Retries policy healthy: {report.retries_policy_healthy}, "
                f"Rate limiters: {report.rate_limiters_operational}",
                f"Checkpoint persistence healthy: {report.checkpoint_persistence_healthy}",
            ],
        )
