from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from core.contracts import RiskLevel


class VerificationGate(StrEnum):
    """Safety gates resulting from confidence and risk analysis."""

    ALLOW_AUTONOMOUS = "allow_autonomous"
    REQUIRE_HUMAN_APPROVAL = "require_human_approval"
    REQUIRE_ADDITIONAL_EVIDENCE = "require_additional_evidence"
    BLOCK = "block"


class CostCategory(StrEnum):
    """Cost telemetry tracking categories."""

    MODEL_CEO = "model_ceo"
    MODEL_WORKERS = "model_workers"
    VOICE_STT_TTS = "voice_stt_tts"
    TELEPHONY = "telephony"
    EMBEDDINGS = "embeddings"
    APIS_EXTERNAL = "apis_external"
    COMPUTE = "compute"


@dataclass(frozen=True)
class SecurityAuditReport:
    """System-wide capability and secret security audit report."""

    timestamp: str
    total_capabilities_audited: int
    read_only_count: int
    harmless_write_count: int
    sensitive_business_count: int
    privileged_count: int
    secret_references_active: int
    credential_leases_valid: bool
    risk_ceiling_violations: list[str] = field(default_factory=list)
    security_score: float = 100.0
    status: str = "SECURE"


@dataclass(frozen=True)
class CostItem:
    """A granular itemized cost entry."""

    id: str
    timestamp: str
    category: CostCategory
    description: str
    units: float
    unit_name: str
    cost_inr: float
    agent_id: str = "system"
    task_id: str | None = None


@dataclass(frozen=True)
class FinopsReport:
    """Aggregated FinOps cost telemetry and unit economics."""

    timestamp: str
    total_spend_inr: float
    currency: str = "INR"
    breakdown_by_category: dict[str, float] = field(default_factory=dict)
    breakdown_by_agent: dict[str, float] = field(default_factory=dict)
    tasks_processed_count: int = 0
    unit_cost_per_task_inr: float = 0.0
    detected_anomalies: list[str] = field(default_factory=list)
    optimization_recommendations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentTelemetry:
    """Performance telemetry record for an individual agent."""

    agent_id: str
    name: str
    domain: str
    tasks_completed: int
    tasks_failed: int
    success_rate_percentage: float
    average_runtime_ms: float
    p95_runtime_ms: float
    total_cost_inr: float
    health_status: str = "HEALTHY"


@dataclass(frozen=True)
class AgentPerformanceReport:
    """Consolidated agent fleet performance and reliability report."""

    timestamp: str
    fleet_size: int
    total_tasks_completed: int
    average_fleet_success_rate: float
    average_fleet_latency_ms: float
    agent_metrics: list[AgentTelemetry] = field(default_factory=list)


@dataclass(frozen=True)
class ConfidenceVerificationResult:
    """Verification outcome evaluating agent confidence against action risk."""

    task_id: str
    capability: str
    risk_level: RiskLevel
    confidence_score: float
    uncertainty_factors: list[str]
    gate: VerificationGate
    rationale: str
    requires_human_approval: bool
    evidence_valid: bool = True


@dataclass(frozen=True)
class ResilienceHealthReport:
    """Operational resilience, rate limit, and checkpoint recovery health."""

    timestamp: str
    retries_policy_healthy: bool
    circuit_breakers_closed: bool
    rate_limiters_operational: bool
    checkpoint_persistence_healthy: bool
    last_checkpoint_timestamp: str | None
    recovery_readiness_score: float = 100.0
    active_alerts: list[str] = field(default_factory=list)
