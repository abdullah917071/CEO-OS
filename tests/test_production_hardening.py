import asyncio
import time

from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app
from core.contracts import CapabilitySpec, RiskLevel
from integrations.contracts import IntegrationHealth, IntegrationType
from integrations.router import CapabilityRouter
from production.contracts import CostCategory, VerificationGate
from production.engine import ProductionHardeningEngine
from production.integration import ProductionHardeningIntegration


def test_production_manifest_and_tool_registration() -> None:
    integration = ProductionHardeningIntegration()
    manifest = integration.manifest()

    assert manifest.name == "production_hardening"
    assert manifest.integration_type == IntegrationType.NATIVE
    assert manifest.domain == "operations"
    assert manifest.risk_ceiling == RiskLevel.READ

    asyncio.run(integration.connect())
    assert integration.status().health == IntegrationHealth.HEALTHY

    tools = integration.tools()
    tool_names = {t.spec.name for t in tools}
    assert tool_names == {
        "production.security.audit",
        "production.cost.overview",
        "production.agent.performance",
        "production.confidence.verify",
        "production.resilience.health",
    }


def test_production_engine_security_audit() -> None:
    engine = ProductionHardeningEngine()
    sample_caps = [
        CapabilitySpec(
            name="files.read",
            description="Read file",
            input_schema={},
            risk=RiskLevel.READ,
            source="native",
        ),
        CapabilitySpec(
            name="files.write",
            description="Write file",
            input_schema={},
            risk=RiskLevel.HARMLESS_WRITE,
            source="native",
        ),
        CapabilitySpec(
            name="comms.email.send",
            description="Send email",
            input_schema={},
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:comms",
        ),
        CapabilitySpec(
            name="meta.ads.create",
            description="Create ad",
            input_schema={},
            risk=RiskLevel.BUSINESS_CHANGE,
            source="integration:meta",
        ),
    ]

    report = engine.audit_security(
        capabilities=sample_caps, active_secret_refs=4, credential_leases_valid=True
    )
    assert report.total_capabilities_audited == 4
    assert report.read_only_count == 1
    assert report.harmless_write_count == 1
    assert report.sensitive_business_count == 1
    assert report.privileged_count == 1
    assert report.security_score == 100.0
    assert report.status == "SECURE"


def test_production_engine_cost_finops() -> None:
    engine = ProductionHardeningEngine()
    overview = engine.get_cost_overview()

    assert overview.total_spend_inr > 0.0
    assert overview.currency == "INR"
    assert "model_ceo" in overview.breakdown_by_category
    assert "voice_stt_tts" in overview.breakdown_by_category
    assert "telephony" in overview.breakdown_by_category
    assert overview.tasks_processed_count >= 100
    assert overview.unit_cost_per_task_inr > 0.0
    assert len(overview.optimization_recommendations) >= 1

    # Record new cost item
    new_item = engine.record_cost(
        category=CostCategory.MODEL_WORKERS,
        description="Deep research token usage",
        units=50000.0,
        unit_name="tokens",
        cost_inr=15.00,
        agent_id="research_agent",
    )
    assert new_item.cost_inr == 15.00
    new_overview = engine.get_cost_overview()
    assert new_overview.total_spend_inr == round(overview.total_spend_inr + 15.00, 2)


def test_production_engine_agent_performance() -> None:
    engine = ProductionHardeningEngine()
    perf = engine.get_agent_performance()

    assert perf.fleet_size >= 4
    assert perf.average_fleet_success_rate >= 90.0
    assert perf.average_fleet_latency_ms > 0.0

    agent_names = {a.agent_id for a in perf.agent_metrics}
    assert "marketing_agent" in agent_names
    assert "finance_agent" in agent_names

    # Record telemetry
    engine.record_agent_telemetry(
        agent_id="marketing_agent",
        name="Marketing Intelligence Agent",
        domain="marketing",
        runtime_ms=39000.0,
        success=True,
        cost_inr=1.20,
    )
    updated_perf = engine.get_agent_performance()
    marketing = next(a for a in updated_perf.agent_metrics if a.agent_id == "marketing_agent")
    assert marketing.tasks_completed == 129


def test_production_confidence_verification_and_safety_gating() -> None:
    engine = ProductionHardeningEngine()

    # 1. High risk (R2) + Low confidence (<0.50) -> BLOCK
    res_block = engine.verify_confidence(
        task_id="t_001",
        capability="comms.email.send",
        risk_level=RiskLevel.EXTERNAL_COMMUNICATION,
        confidence_score=0.42,
    )
    assert res_block.gate == VerificationGate.BLOCK
    assert not res_block.requires_human_approval

    # 2. High risk (R2) + Medium confidence (0.72) -> REQUIRE_HUMAN_APPROVAL
    res_approval = engine.verify_confidence(
        task_id="t_002",
        capability="meta.adset.update",
        risk_level=RiskLevel.BUSINESS_CHANGE,
        confidence_score=0.72,
        evidence=["Ad CPA increased 22%"],
    )
    assert res_approval.gate == VerificationGate.REQUIRE_HUMAN_APPROVAL
    assert res_approval.requires_human_approval

    # 3. High risk (R2) + High confidence (0.95) + Evidence -> ALLOW_AUTONOMOUS
    res_allow = engine.verify_confidence(
        task_id="t_003",
        capability="comms.followup.schedule",
        risk_level=RiskLevel.EXTERNAL_COMMUNICATION,
        confidence_score=0.95,
        evidence=["Invoice #INV-2026-088 is 18 days overdue"],
    )
    assert res_allow.gate == VerificationGate.ALLOW_AUTONOMOUS
    assert not res_allow.requires_human_approval

    # 4. Low risk (R0) + Low confidence (0.45) -> REQUIRE_ADDITIONAL_EVIDENCE
    res_r0_low = engine.verify_confidence(
        task_id="t_004",
        capability="business.finance.overview",
        risk_level=RiskLevel.READ,
        confidence_score=0.45,
    )
    assert res_r0_low.gate == VerificationGate.REQUIRE_ADDITIONAL_EVIDENCE

    # 5. Low risk (R0) + High confidence (0.90) -> ALLOW_AUTONOMOUS
    res_r0_high = engine.verify_confidence(
        task_id="t_005",
        capability="business.finance.overview",
        risk_level=RiskLevel.READ,
        confidence_score=0.90,
    )
    assert res_r0_high.gate == VerificationGate.ALLOW_AUTONOMOUS


def test_production_fast_path_router() -> None:
    engine = ProductionHardeningEngine()

    fast_chrome = engine.route_fast_path("Open Chrome")
    assert fast_chrome is not None
    assert fast_chrome["fast_path"] is True
    assert fast_chrome["app"] == "Google Chrome"
    assert fast_chrome["estimated_latency_ms"] <= 200

    fast_ping = engine.route_fast_path("health")
    assert fast_ping is not None
    assert fast_ping["status"] == "healthy"

    complex_cmd = engine.route_fast_path("Analyze our businesses and restructure marketing spend")
    assert complex_cmd is None


def test_capability_router_production_domain() -> None:
    router = CapabilityRouter()
    domains = router.classify_domains("production hardening cost and security audit")
    assert "integrations" in domains


def test_api_production_endpoints() -> None:
    with TestClient(app) as client:
        # 1. Security Audit
        sec_resp = client.get("/api/v1/production/security/audit")
        assert sec_resp.status_code == 200
        sec_data = sec_resp.json()
        assert sec_data["status"] == "SECURE"
        assert sec_data["total_capabilities_audited"] >= 10

        # 2. Cost Overview
        cost_resp = client.get("/api/v1/production/cost/overview")
        assert cost_resp.status_code == 200
        cost_data = cost_resp.json()
        assert cost_data["total_spend_inr"] > 0.0
        assert "model_ceo" in cost_data["breakdown_by_category"]

        # 3. Agent Performance
        perf_resp = client.get("/api/v1/production/agents/performance")
        assert perf_resp.status_code == 200
        perf_data = perf_resp.json()
        assert perf_data["fleet_size"] >= 4
        assert perf_data["average_fleet_success_rate"] >= 90.0

        # 4. Confidence Verify
        conf_resp = client.post(
            "/api/v1/production/confidence/verify",
            json={
                "task_id": "test_task_001",
                "capability": "meta.adset.update",
                "risk_level": "r2",
                "confidence_score": 0.75,
                "evidence": ["Ad CTR dropped below 0.5%"],
            },
        )
        assert conf_resp.status_code == 200
        conf_data = conf_resp.json()
        assert conf_data["gate"] == "require_human_approval"
        assert conf_data["requires_human_approval"] is True

        # 5. Resilience Health
        resil_resp = client.get("/api/v1/production/resilience/health")
        assert resil_resp.status_code == 200
        resil_data = resil_resp.json()
        assert resil_data["recovery_readiness_score"] == 100.0
        assert resil_data["checkpoint_persistence_healthy"] is True


def test_production_hardening_acceptance_scenario() -> None:
    """Roadmap Acceptance Test for Phase 21:

    'CEO, run a production hardening audit covering security, FinOps costs, agent performance...'
    """
    with TestClient(app) as client:
        message = (
            "CEO, run a production hardening audit covering "
            "security, FinOps costs, agent performance, and resilience"
        )
        resp = client.post("/api/v1/chat/messages", json={"message": message})
        assert resp.status_code == 202
        task_id = resp.json()["id"]

        deadline = time.time() + 10.0
        task: dict[str, object] = {}
        while time.time() < deadline:
            task_resp = client.get(f"/api/v1/tasks/{task_id}")
            assert task_resp.status_code == 200
            task = task_resp.json()
            if task["status"] in {"success", "failed", "cancelled"}:
                break
            time.sleep(0.1)

        assert task["status"] == "success", f"Task failed with error: {task.get('error')}"
        plan = task.get("plan", {})
        assert isinstance(plan, dict)
        steps = plan.get("steps", [])
        assert len(steps) >= 3

        capabilities_executed = [s["capability"] for s in steps]
        assert "production.security.audit" in capabilities_executed
        assert "production.cost.overview" in capabilities_executed

        result = task.get("result", {})
        assert isinstance(result, dict)
        evidence = result.get("evidence", [])
        assert len(evidence) >= 1
