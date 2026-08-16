from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from agency import (
    AgencyAgentsEngine,
    AgencyIntegration,
)
from agents.repository import AgentRepository
from agents.runtime import AgentPolicyError, AgentRuntime, DeterministicResearchExecutor
from agents.templates import AgentTemplateRegistry
from agents.tools import agent_tools
from apps.api.src.ceo_os_api.checkpoints import open_checkpointer
from apps.api.src.ceo_os_api.config import get_settings
from apps.api.src.ceo_os_api.database import (
    TaskRecord,
    TaskRepository,
    create_database,
    initialize_schema,
)
from apps.api.src.ceo_os_api.events import EventHub
from apps.api.src.ceo_os_api.planner import DeterministicProvider
from apps.api.src.ceo_os_api.runtime import CeoRuntime, TaskRunner

logger = logging.getLogger(__name__)
from apps.api.src.ceo_os_api.schemas import (
    AgencyExecuteRequest,
    AgencyExecuteResponse,
    AgencyMatchRequest,
    AgencyMatchResponse,
    AgencySkillSchema,
    AgencySkillsListResponse,
    AgencySpawnRequest,
    AgencySpawnResponse,
    AgentAssignmentResponse,
    AgentCloneRequest,
    AgentCreateRequest,
    AgentMessageRequest,
    AgentMessageResponse,
    AgentPerformanceResponse,
    AgentResponse,
    AgentUpdateRequest,
    ApiBuildResponse,
    ApiIngestRequest,
    ApiInspectResponse,
    BusinessAffordabilityResponse,
    BusinessDealSchema,
    BusinessExecutiveOverviewResponse,
    BusinessFinancialOverviewResponse,
    BusinessInventoryItemSchema,
    BusinessInvoiceSchema,
    BusinessOperationsHealthResponse,
    BusinessSalesPipelineResponse,
    CallInitiateRequest,
    CallResponse,
    CapabilityResponse,
    CapabilityRouteRequest,
    CapabilityRouteResponse,
    CeoAgentReflectRequest,
    CeoAgentReflectResponse,
    CeoAgentRunRequest,
    CeoAgentRunResponse,
    CeoAgentSubagentSpawnRequest,
    CeoAgentSubagentSpawnResponse,
    CeoAgentTrajectoriesResponse,
    CommsConversationAnalyzeRequest,
    CommsEmailSendRequest,
    CommsFollowupResponse,
    CommsFollowupScheduleRequest,
    CommsMessageResponse,
    CommsNotificationBroadcastRequest,
    CommsNotificationResponse,
    CommsSmsSendRequest,
    CommsWhatsappSendRequest,
    ConfidenceVerifyRequest,
    ConfidenceVerifyResponse,
    CuaActionRequestSchema,
    CuaActionResponseSchema,
    CuaAppsResponse,
    CuaExecuteRequestSchema,
    CuaExecuteResponseSchema,
    CuaStatusResponse,
    DelegationRequest,
    FinopsCostResponse,
    GoalCreateRequest,
    GoalResponse,
    GstackCeoReviewRequest,
    GstackCeoReviewResponse,
    GstackEngReviewRequest,
    GstackEngReviewResponse,
    GstackOfficeHoursRequest,
    GstackOfficeHoursResponse,
    GstackPipelineRequest,
    GstackPipelineResponse,
    GstackQaRequest,
    GstackQaResponse,
    GstackShipRequest,
    GstackShipResponse,
    GstackStaffReviewRequest,
    GstackStaffReviewResponse,
    HermesReflectResponse,
    HermesRunResponse,
    HermesSubagentSpawnResponse,
    HermesTrajectoriesResponse,
    IntegrationStatusResponse,
    InteractiveChatRequest,
    InteractiveChatResponse,
    MarketingCreativePerformanceSchema,
    MarketingSnapshotResponse,
    McpInstallRequest,
    MemoryCorrectRequest,
    MemoryCreateRequest,
    MemoryResponse,
    MessageRequest,
    MetaAccountResponse,
    MetaAdCreateRequest,
    MetaAdResponse,
    MetaAdSetCreateRequest,
    MetaAdSetResponse,
    MetaCampaignCreateRequest,
    MetaCampaignReportResponse,
    MetaCampaignResponse,
    MetaCampaignUpdateRequest,
    MetaCreativeCreateRequest,
    MetaCreativeResponse,
    MetaInsightResponse,
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
    OAuthTokenResponse,
    ProactiveEvaluateResponse,
    ProactiveInsightResponse,
    ProfitDiagnosticResponse,
    ResilienceHealthResponse,
    RestaurantBookingRequest,
    RestaurantBookingResponse,
    RouterCandidateSchema,
    RouterCreateRequest,
    RouterDelegateRequest,
    RouterDelegateResponse,
    RouterFeedbackRequest,
    RouterSearchRequest,
    RouterSearchResponse,
    RouterTeamRequest,
    RouterTeamResponse,
    SecretRegisterRequest,
    SecretResponse,
    SecurityAuditResponse,
    SkillCreateRequest,
    SkillDefinitionResponse,
    SkillDisableRequest,
    SkillExecuteRequest,
    SkillExecutionResponse,
    SkillTestRequest,
    SkillTestResponse,
    SkillVersionRequest,
    TaskResponse,
    TriggerCreateRequest,
    TriggerResponse,
)
from apps.desktop import CuaDesktopApp
from browser.engine import PlaywrightBrowserEngine
from browser.policy import BrowserPolicy, parse_allowed_origins
from browser.tools import browser_tools
from ceo_agent import (
    CeoAIAgent,
    CeoExecutiveIntegration,
    CeoModelProvider,
    CeoSubagentSpec,
    DeterministicCeoEngine,
    OpenAiCompatibleCeoEngine,
    OpenRouterModelProvider,
)
from communications.messaging import (
    CommunicationsIntegration,
    CommunicationsManager,
    MessageChannel,
    MessageStatus,
    Priority,
)
from communications.telephony import (
    CallManager,
    CallRecord,
    TelephonyIntegration,
)
from computer.client import MacHelperClient
from computer.controller import ComputerController, ComputerPolicy
from computer.tools import computer_tools
from core.capabilities import CapabilityRegistry
from core.contracts import RiskLevel, TaskControl, TaskStatus
from core.model_router import ModelRouter
from gstack import (
    GstackEngine,
    GstackIntegration,
)
from integrations.autobuilder import (
    ApiAutoBuilderEngine,
    ApiAutoBuilderIntegration,
)
from integrations.google import GoogleEcosystemIntegration
from integrations.mcp_adapter import MCP_AVAILABLE, McpServerConfig, McpServerProvider
from integrations.mcp_config import load_mcp_configs
from integrations.meta import (
    MetaClient,
    MetaMarketingIntegration,
)
from integrations.native import SystemInfoIntegration
from integrations.oauth import OAuthManager
from integrations.registry import IntegrationRegistry
from integrations.router import CapabilityRouter
from integrations.secrets import SecretBroker
from intelligence.business import (
    BusinessExecutiveEngine,
    BusinessIntelligenceIntegration,
)
from intelligence.marketing import (
    MarketingIntelligenceEngine,
    MarketingIntelligenceIntegration,
)
from memory.embedding import FeatureHashEmbeddingProvider
from memory.service import MemoryService, Provenance, initialize_memory_schema
from memory.tools import memory_tools
from proactive import (
    ProactiveCeoEngine,
    ProactiveIntegration,
)
from production import (
    ProductionHardeningEngine,
    ProductionHardeningIntegration,
)
from skills import (
    SkillsEngine,
    SkillsIntegration,
    SkillStep,
)
from tools.builtin import built_in_tools
from vision.driver import CuaSdkDriver
from vision.runtime import VisionPolicy, VisionRuntime
from vision.tools import vision_tools
from voice.contracts import SpeechProvider, TranscriptionProvider
from voice.providers import OpenAISpeechProvider, OpenAITranscriptionProvider, Utf8VoiceProvider
from voice.runtime import VoicePolicy, VoicePolicyError, VoiceRuntime
from workflows.restaurant import (
    ReservationRequest,
    RestaurantBookingWorkflow,
    RestaurantWorkflowIntegration,
)

settings = get_settings()
engine, session_factory = create_database(settings.database_url)
redis = Redis.from_url(settings.redis_url, decode_responses=True)
events = EventHub()
secret_broker = SecretBroker()
oauth_manager = OAuthManager(secret_broker)
capability_router = CapabilityRouter()
agent_repository = AgentRepository(session_factory)
agent_template_registry = AgentTemplateRegistry()
agency_engine = AgencyAgentsEngine()
agency_engine.register_all_templates(agent_template_registry)
agent_runtime = AgentRuntime(
    agent_repository,
    agent_template_registry,
    DeterministicResearchExecutor(),
    events,
)
memory = MemoryService(session_factory, engine.dialect.name, FeatureHashEmbeddingProvider())
computer = ComputerController(
    MacHelperClient(settings.computer_helper_path),
    ComputerPolicy(
        effects_enabled=settings.computer_effects_enabled,
        allowed_bundle_ids=frozenset(
            value.strip()
            for value in settings.computer_allowed_bundle_ids.split(",")
            if value.strip()
        ),
    ),
)
cua_app = CuaDesktopApp(
    helper_path=settings.computer_helper_path,
    effects_enabled=settings.computer_effects_enabled,
)
browser_policy = BrowserPolicy(
    allowed_origins=parse_allowed_origins(settings.browser_allowed_origins),
    upload_root=settings.workspace_root,
    download_root=settings.workspace_root / "downloads",
    effects_enabled=settings.browser_effects_enabled,
    persistent_profiles_enabled=settings.browser_persistent_profiles_enabled,
)
browser = PlaywrightBrowserEngine(
    browser_policy,
    settings.workspace_root / ".ceo-os/browser",
    headless=settings.browser_headless,
    enabled=settings.browser_enabled,
    browsers_path=settings.browser_browsers_path,
    timeout_ms=settings.browser_timeout_ms,
)
vision = VisionRuntime(
    CuaSdkDriver(enabled=settings.vision_enabled),
    VisionPolicy(
        effects_enabled=settings.vision_effects_enabled,
        allowed_app_names=frozenset(
            value.strip() for value in settings.vision_allowed_app_names.split(",") if value.strip()
        ),
        foreground_escalation_enabled=settings.vision_foreground_escalation_enabled,
    ),
)
voice_transcriber: TranscriptionProvider
voice_speaker: SpeechProvider
if settings.voice_provider == "deterministic":
    voice_transcriber = voice_speaker = Utf8VoiceProvider()
else:
    voice_transcriber = OpenAITranscriptionProvider(
        settings.openai_api_key,
        settings.voice_transcription_model,
        settings.voice_realtime_url,
    )
    voice_speaker = OpenAISpeechProvider(
        settings.openai_api_key,
        settings.voice_speech_model,
        settings.voice_name,
        settings.voice_api_base_url,
    )
voice = VoiceRuntime(voice_transcriber, voice_speaker, VoicePolicy(enabled=settings.voice_enabled))
integration_registry = IntegrationRegistry()
if settings.system_info_integration_enabled:
    integration_registry.register(SystemInfoIntegration(settings.workspace_root))
google_integration = GoogleEcosystemIntegration(secret_broker=secret_broker)
integration_registry.register(google_integration)
telephony_integration = TelephonyIntegration(
    memory_service=memory,
    secret_broker=secret_broker,
)
integration_registry.register(telephony_integration)
restaurant_workflow = RestaurantBookingWorkflow(
    google_client=google_integration._client,
    call_manager=telephony_integration.manager,
    memory_service=memory,
)
restaurant_integration = RestaurantWorkflowIntegration(
    workflow=restaurant_workflow,
    secret_broker=secret_broker,
)
integration_registry.register(restaurant_integration)
meta_integration = MetaMarketingIntegration(secret_broker=secret_broker)
integration_registry.register(meta_integration)
marketing_integration = MarketingIntelligenceIntegration(secret_broker=secret_broker)
integration_registry.register(marketing_integration)
comms_integration = CommunicationsIntegration(
    memory_service=memory,
    secret_broker=secret_broker,
)
integration_registry.register(comms_integration)
business_integration = BusinessIntelligenceIntegration(secret_broker=secret_broker)
integration_registry.register(business_integration)
skills_integration = SkillsIntegration(
    registry_getter=lambda: capabilities,
    secret_broker=secret_broker,
)
integration_registry.register(skills_integration)
autobuilder_engine = ApiAutoBuilderEngine(
    integration_registry=integration_registry,
    secret_broker=secret_broker,
)
autobuilder_integration = ApiAutoBuilderIntegration(
    engine=autobuilder_engine,
    secret_broker=secret_broker,
)
integration_registry.register(autobuilder_integration)
proactive_integration = ProactiveIntegration()
integration_registry.register(proactive_integration)
production_integration = ProductionHardeningIntegration()
integration_registry.register(production_integration)
agency_integration = AgencyIntegration(engine=agency_engine)
integration_registry.register(agency_integration)
openrouter_key = settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
openrouter_model = settings.model_name or "nvidia/nemotron-3.5-lightning:free"
openrouter_base = settings.openrouter_base_url or "https://openrouter.ai/api/v1"

is_pytest = (
    "pytest" in sys.modules
    or "PYTEST_CURRENT_TEST" in os.environ
    or os.getenv("CEO_OS_ENV") == "test"
)

hermes_llm = (
    OpenAiCompatibleCeoEngine(
        base_url=openrouter_base,
        api_key=openrouter_key,
        model_name=openrouter_model,
    )
    if openrouter_key and not openrouter_key.startswith("mock_") and not is_pytest
    else DeterministicCeoEngine()
)
ceo_agent = CeoAIAgent(llm=hermes_llm)
hermes_agent = ceo_agent
ceo_integration = CeoExecutiveIntegration(agent=ceo_agent)
hermes_integration = ceo_integration
integration_registry.register(ceo_integration)
gstack_engine = GstackEngine()
gstack_integration = GstackIntegration(engine=gstack_engine)
integration_registry.register(gstack_integration)
for mcp_config in load_mcp_configs(settings.mcp_servers_config, settings.mcp_servers or None):
    if mcp_config.enabled and MCP_AVAILABLE:
        integration_registry.register(McpServerProvider(mcp_config))
capabilities: CapabilityRegistry  # assigned after integration connect in lifespan
models = ModelRouter(
    {
        "deterministic": DeterministicProvider(),
        "ceo-agent": CeoModelProvider(llm=hermes_llm),
        "hermes": CeoModelProvider(llm=hermes_llm),
        "openrouter": OpenRouterModelProvider(
            api_key=openrouter_key,
            model_name=openrouter_model,
            base_url=openrouter_base,
        ),
    },
    "deterministic" if is_pytest else settings.model_provider,
)
tasks = TaskRepository(session_factory)


def get_runtime(request: Request) -> CeoRuntime:
    return cast(CeoRuntime, request.app.state.runtime)


def get_runner(request: Request) -> TaskRunner:
    return cast(TaskRunner, request.app.state.runner)


def get_memory(request: Request) -> MemoryService:
    return cast(MemoryService, request.app.state.memory)


def get_computer(request: Request) -> ComputerController:
    return getattr(request.app.state, "computer", computer)


def get_cua(request: Request) -> CuaDesktopApp:
    return getattr(request.app.state, "cua_app", cua_app)


def get_browser(request: Request) -> PlaywrightBrowserEngine:
    return cast(PlaywrightBrowserEngine, request.app.state.browser)


def get_vision(request: Request) -> VisionRuntime:
    return cast(VisionRuntime, request.app.state.vision)


def get_voice(request: Request) -> VoiceRuntime:
    return cast(VoiceRuntime, request.app.state.voice)


def get_telephony(request: Request) -> CallManager:
    return cast(CallManager, request.app.state.telephony)


def get_restaurant_workflow(request: Request) -> RestaurantBookingWorkflow:
    return cast(RestaurantBookingWorkflow, request.app.state.restaurant_workflow)


def get_meta(request: Request) -> MetaClient:
    return cast(MetaClient, request.app.state.meta)


def get_marketing_intelligence(request: Request) -> MarketingIntelligenceEngine:
    return cast(MarketingIntelligenceEngine, request.app.state.marketing_intelligence)


def get_comms(request: Request) -> CommunicationsManager:
    return cast(CommunicationsManager, request.app.state.comms)


def get_business_intelligence(request: Request) -> BusinessExecutiveEngine:
    return cast(BusinessExecutiveEngine, request.app.state.business_intelligence)


def get_skills(request: Request) -> SkillsEngine:
    return cast(SkillsEngine, request.app.state.skills)


def get_autobuilder(request: Request) -> ApiAutoBuilderEngine:
    return cast(ApiAutoBuilderEngine, request.app.state.autobuilder)


def get_proactive(request: Request) -> ProactiveCeoEngine:
    return cast(ProactiveCeoEngine, request.app.state.proactive)


def get_production(request: Request) -> ProductionHardeningEngine:
    return cast(ProductionHardeningEngine, request.app.state.production)


def get_agency(request: Request) -> AgencyAgentsEngine:
    return cast(AgencyAgentsEngine, request.app.state.agency)


def get_ceo_agent(request: Request) -> CeoAIAgent:
    return getattr(
        request.app.state,
        "ceo_agent",
        getattr(request.app.state, "hermes", ceo_agent),
    )


def get_hermes(request: Request) -> CeoAIAgent:
    return get_ceo_agent(request)


def get_gstack(request: Request) -> GstackEngine:
    return getattr(request.app.state, "gstack", gstack_engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global capabilities  # noqa: PLW0603
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    await initialize_schema(engine)
    await initialize_memory_schema(engine)
    await browser.start()
    await vision.start()
    await integration_registry.connect_all()
    capabilities = CapabilityRegistry(
        [
            *built_in_tools(settings.workspace_root),
            *agent_tools(agent_runtime),
            *memory_tools(memory),
            *computer_tools(computer, include_effects=settings.computer_effects_enabled),
            *browser_tools(browser, include_effects=settings.browser_effects_enabled),
            *vision_tools(vision, include_effects=settings.vision_effects_enabled),
            *integration_registry.all_tools(),
        ]
    )
    hermes_agent.capabilities = capabilities
    gstack_engine._capabilities = capabilities

    def _sync_integration_tools(reg: IntegrationRegistry) -> None:
        global capabilities
        capabilities.unregister_by_source("mcp")
        capabilities.unregister_by_source("integration")
        capabilities.unregister_by_source("workflow")
        for tool in reg.all_tools():
            capabilities.register(tool)

    integration_registry.add_listener(_sync_integration_tools)

    async with open_checkpointer(settings.database_url) as checkpointer:
        runtime = CeoRuntime(tasks, capabilities, models, events, checkpointer, memory)
        runner = TaskRunner(runtime)
        app.state.runtime, app.state.runner, app.state.memory = runtime, runner, memory
        app.state.computer = computer
        app.state.browser = browser
        app.state.vision = vision
        app.state.voice = voice
        app.state.agents = agent_runtime
        app.state.integrations = integration_registry
        app.state.telephony = telephony_integration.manager
        app.state.restaurant_workflow = restaurant_workflow
        app.state.meta = meta_integration.client
        app.state.marketing_intelligence = marketing_integration.engine
        app.state.comms = comms_integration.manager
        app.state.business_intelligence = business_integration.engine
        app.state.skills = skills_integration.engine
        app.state.autobuilder = autobuilder_engine
        app.state.proactive = proactive_integration.engine
        app.state.production = production_integration.engine
        app.state.agency = agency_engine
        app.state.hermes = hermes_agent
        app.state.gstack = gstack_engine
        app.state.secrets = secret_broker
        app.state.oauth = oauth_manager
        app.state.router = capability_router
        await agent_runtime.initialize()
        await runner.recover()
        yield
        await agent_runtime.shutdown()
        await voice.shutdown()
        await runner.shutdown()
    await integration_registry.disconnect_all()
    await browser.shutdown()
    await vision.shutdown()
    await redis.aclose()
    await engine.dispose()


app = FastAPI(title="CEO OS API", version="0.10.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "service": "ceo-os-api"}


@app.get("/health/ready")
async def ready() -> dict[str, object]:
    checks: dict[str, bool] = {"database": False, "redis": False}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        checks["redis"] = bool(await redis.ping())
    except Exception:
        pass
    if not all(checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}


@app.get("/api/v1/capabilities", response_model=list[CapabilityResponse])
async def list_capabilities() -> list[dict[str, object]]:
    return [asdict(spec) for spec in capabilities.list()]


def get_agent_runtime(request: Request) -> AgentRuntime:
    return cast(AgentRuntime, request.app.state.agents)


@app.get("/api/v1/agents", response_model=list[AgentResponse])
async def list_agents() -> object:
    return await agent_repository.list_agents()


@app.post("/api/v1/agents", response_model=AgentResponse, status_code=201)
async def create_agent(request: Request, body: AgentCreateRequest) -> object:
    try:
        return await get_agent_runtime(request).create_agent(
            name=body.name,
            template_name=body.template_name,
            parent_id=str(body.parent_id) if body.parent_id else None,
            allowed_capabilities=body.allowed_capabilities,
            data_scope=body.data_scope,
            max_runtime_seconds=body.max_runtime_seconds,
            max_cost_units=body.max_cost_units,
            max_concurrency=body.max_concurrency,
        )
    except AgentPolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.patch("/api/v1/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(request: Request, agent_id: UUID, body: AgentUpdateRequest) -> object:
    try:
        return await get_agent_runtime(request).update_agent(
            str(agent_id),
            name=body.name,
            max_runtime_seconds=body.max_runtime_seconds,
            max_cost_units=body.max_cost_units,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
    except AgentPolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/agents/{agent_id}/clone", response_model=AgentResponse, status_code=201)
async def clone_agent(request: Request, agent_id: UUID, body: AgentCloneRequest) -> object:
    try:
        return await get_agent_runtime(request).clone_agent(str(agent_id), body.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
    except AgentPolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


async def control_agent(request: Request, agent_id: UUID, action: str) -> object:
    try:
        method = getattr(get_agent_runtime(request), f"{action}_agent")
        return await method(str(agent_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
    except AgentPolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/agents/{agent_id}/pause", response_model=AgentResponse)
async def pause_agent(request: Request, agent_id: UUID) -> object:
    return await control_agent(request, agent_id, "pause")


@app.post("/api/v1/agents/{agent_id}/resume", response_model=AgentResponse)
async def resume_agent(request: Request, agent_id: UUID) -> object:
    return await control_agent(request, agent_id, "resume")


@app.post("/api/v1/agents/{agent_id}/terminate", response_model=AgentResponse)
async def terminate_agent(request: Request, agent_id: UUID) -> object:
    return await control_agent(request, agent_id, "terminate")


@app.post("/api/v1/delegations")
async def create_delegation(request: Request, body: DelegationRequest) -> object:
    try:
        return await get_agent_runtime(request).delegate(
            body.objective,
            body.items,
            worker_count=body.worker_count,
            template_name=body.template_name,
            context=body.context,
        )
    except AgentPolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/agent-assignments", response_model=list[AgentAssignmentResponse])
async def list_agent_assignments(limit: int = Query(default=100, ge=1, le=200)) -> object:
    return await agent_repository.list_assignments(limit)


@app.post("/api/v1/agent-messages", response_model=AgentMessageResponse, status_code=201)
async def send_agent_message(request: Request, body: AgentMessageRequest) -> object:
    try:
        return await get_agent_runtime(request).send_message(
            str(body.sender_id),
            str(body.recipient_id),
            body.message_type,
            body.payload,
            str(body.assignment_id) if body.assignment_id else None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc


@app.get("/api/v1/agents/{agent_id}/messages", response_model=list[AgentMessageResponse])
async def agent_inbox(agent_id: UUID, limit: int = Query(default=100, ge=1, le=200)) -> object:
    if await agent_repository.get_agent(str(agent_id)) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await agent_repository.inbox(str(agent_id), limit)


# ── Universal Agent Router Endpoints ───────────────────────────────────────────


@app.post("/api/v1/router/search", response_model=RouterSearchResponse)
async def router_search(body: RouterSearchRequest) -> object:
    from agents.tools import AgentSearchTool

    tool = AgentSearchTool()
    div_dict = {"division": body.division} if body.division else {}
    res = await tool.execute({"query": body.query, "limit": body.limit, **div_dict})
    out: dict[str, Any] = res.output if isinstance(res.output, dict) else {}
    candidates = [
        RouterCandidateSchema(
            agent_id=c["agent_id"],
            name=c["name"],
            role=c["role"],
            division=c["division"],
            relevance_score=c["relevance_score"],
            match_reasons=c.get("match_reasons", []),
            default_tools=c.get("default_tools", []),
            score_rating=c.get("score_rating", 5.0),
            success_rate=c.get("success_rate", 1.0),
        )
        for c in out.get("candidates", [])
    ]
    return RouterSearchResponse(query=body.query, count=len(candidates), candidates=candidates)


@app.get("/api/v1/router/agents/{agent_id}")
async def router_inspect(agent_id: str) -> object:
    from agents.tools import AgentInspectTool

    tool = AgentInspectTool()
    res = await tool.execute({"agent_id": agent_id})
    out: dict[str, Any] = res.output if isinstance(res.output, dict) else {}
    if out.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return res.output


@app.post("/api/v1/router/delegate", response_model=RouterDelegateResponse)
async def router_delegate(body: RouterDelegateRequest) -> object:
    from agents.tools import AgentDelegateTool

    tool = AgentDelegateTool()
    res = await tool.execute(
        {
            "agent_id": body.agent_id,
            "task": body.task,
            "deliverable": body.deliverable,
            "do_not_modify_production": body.do_not_modify_production,
        }
    )
    out: dict[str, Any] = res.output if isinstance(res.output, dict) else {}
    if out.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"Agent '{body.agent_id}' not found")
    return RouterDelegateResponse(
        status=out.get("status", "success"),
        agent=out.get("agent", body.agent_id),
        role=out.get("role", "Specialist"),
        summary=out.get("summary", ""),
        findings=out.get("findings", []),
        recommendations=out.get("recommendations", []),
        evidence=out.get("evidence", []),
        confidence=float(out.get("confidence", 0.9)),
    )


@app.post("/api/v1/router/team", response_model=RouterTeamResponse)
async def router_spawn_team(body: RouterTeamRequest) -> object:
    from agents.tools import AgentSpawnTeamTool

    tool = AgentSpawnTeamTool()
    res = await tool.execute({"objective": body.objective, "max_specialists": body.max_specialists})
    out: dict[str, Any] = res.output if isinstance(res.output, dict) else {}
    return RouterTeamResponse(
        status=out.get("status", "SUCCESS"),
        objective=out.get("objective", body.objective),
        lead_agent=out.get("lead_agent", "ceo"),
        team_size=out.get("team_size", 1),
        team_members=out.get("team_members", []),
        stages_executed=out.get("stages_executed", 1),
        stage_results=out.get("stage_results", []),
        findings=out.get("findings", []),
        recommendations=out.get("recommendations", []),
        evidence=out.get("evidence", []),
        synthesis=out.get("synthesis", ""),
    )


@app.post("/api/v1/router/create")
async def router_create_agent(body: RouterCreateRequest) -> object:
    from agents.tools import AgentCreateTool

    tool = AgentCreateTool()
    args: dict[str, Any] = {
        "name": body.name,
        "role": body.role,
        "division": body.division,
        "mission": body.mission,
    }
    if body.tools:
        args["tools"] = body.tools
    res = await tool.execute(args)
    return res.output


@app.post("/api/v1/router/feedback")
async def router_feedback(body: RouterFeedbackRequest) -> object:
    from agents.tools import get_global_agent_registry

    reg = get_global_agent_registry()
    await reg.record_task_outcome(
        agent_id=body.agent_id,
        success=body.success,
        confidence=body.confidence,
        cost=body.cost,
        rating=body.rating,
    )
    return {"status": "SUCCESS", "message": f"Recorded feedback for agent '{body.agent_id}'"}


@app.get("/api/v1/activity")
async def list_activity(limit: int = Query(default=50, ge=1, le=200)) -> object:
    return await events.recent(limit)


@app.get("/api/v1/computer/status")
async def computer_status(request: Request) -> object:
    return await get_computer(request).status()


@app.post("/api/v1/computer/stop")
async def stop_computer(request: Request) -> object:
    return get_computer(request).stop()


@app.post("/api/v1/computer/resume")
async def resume_computer(request: Request) -> object:
    return get_computer(request).resume()


@app.get("/api/v1/browser/status")
async def browser_status(request: Request) -> object:
    return get_browser(request).status()


@app.post("/api/v1/browser/stop")
async def stop_browser(request: Request) -> object:
    return await get_browser(request).stop()


@app.post("/api/v1/browser/resume")
async def resume_browser(request: Request) -> object:
    return get_browser(request).resume()


@app.get("/api/v1/vision/status")
async def vision_status(request: Request) -> object:
    return await get_vision(request).status()


@app.post("/api/v1/vision/stop")
async def stop_vision(request: Request) -> object:
    return await get_vision(request).stop()


@app.post("/api/v1/vision/resume")
async def resume_vision(request: Request) -> object:
    return await get_vision(request).resume()


@app.get("/api/v1/voice/status")
async def voice_status(request: Request) -> object:
    return get_voice(request).status()


def get_integrations(request: Request) -> IntegrationRegistry:
    return cast(IntegrationRegistry, request.app.state.integrations)


def get_secret_broker(request: Request) -> SecretBroker:
    return cast(SecretBroker, request.app.state.secrets)


def get_oauth_manager(request: Request) -> OAuthManager:
    return cast(OAuthManager, request.app.state.oauth)


def get_capability_router(request: Request) -> CapabilityRouter:
    return cast(CapabilityRouter, request.app.state.router)


@app.get("/api/v1/integrations", response_model=list[IntegrationStatusResponse])
async def list_integrations(request: Request) -> object:
    registry = get_integrations(request)
    return [
        {
            "name": s.name,
            "version": s.version,
            "description": s.description,
            "integration_type": s.integration_type,
            "health": s.health,
            "tool_count": s.tool_count,
            "risk_ceiling": s.risk_ceiling,
            "enabled": s.enabled,
            "domain": s.domain,
            "connected_at": s.connected_at.isoformat() if s.connected_at else None,
            "error": s.error,
        }
        for s in registry.list_integrations()
    ]


@app.get("/api/v1/integrations/{name}/status", response_model=IntegrationStatusResponse)
async def integration_status(request: Request, name: str) -> object:
    provider = get_integrations(request).get(name)
    if provider is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    s = provider.status()
    return {
        "name": s.name,
        "version": s.version,
        "description": s.description,
        "integration_type": s.integration_type,
        "health": s.health,
        "tool_count": s.tool_count,
        "risk_ceiling": s.risk_ceiling,
        "enabled": s.enabled,
        "domain": s.domain,
        "connected_at": s.connected_at.isoformat() if s.connected_at else None,
        "error": s.error,
    }


@app.get("/api/v1/integrations/{name}/manifest")
async def integration_manifest(request: Request, name: str) -> object:
    provider = get_integrations(request).get(name)
    if provider is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    if hasattr(provider, "manifest"):
        m = provider.manifest()
        return {
            "name": m.name,
            "version": m.version,
            "description": m.description,
            "integration_type": m.integration_type,
            "domain": m.domain,
            "risk_ceiling": m.risk_ceiling,
            "required_credentials": m.required_credentials,
            "rate_limits": m.rate_limits,
            "enabled": m.enabled,
        }
    s = provider.status()
    return {
        "name": s.name,
        "version": s.version,
        "description": s.description,
        "integration_type": s.integration_type,
        "domain": s.domain,
        "risk_ceiling": s.risk_ceiling,
        "required_credentials": [],
        "rate_limits": {},
        "enabled": s.enabled,
    }


@app.post("/api/v1/integrations/mcp", response_model=IntegrationStatusResponse, status_code=201)
async def install_mcp_integration(request: Request, body: McpInstallRequest) -> object:
    registry = get_integrations(request)
    broker = get_secret_broker(request)
    config = McpServerConfig(
        name=body.name,
        command=body.command,
        args=body.args,
        env=body.env,
        domain=body.domain,
        risk_ceiling=RiskLevel(body.risk_ceiling),
        enabled=body.enabled,
        timeout_seconds=body.timeout_seconds,
    )
    try:
        status = await registry.install_mcp(config, secret_broker=broker)
        return {
            "name": status.name,
            "version": status.version,
            "description": status.description,
            "integration_type": status.integration_type,
            "health": status.health,
            "tool_count": status.tool_count,
            "risk_ceiling": status.risk_ceiling,
            "enabled": status.enabled,
            "domain": status.domain,
            "connected_at": status.connected_at.isoformat() if status.connected_at else None,
            "error": status.error,
        }
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/v1/integrations/{name}")
async def uninstall_integration(request: Request, name: str) -> object:
    registry = get_integrations(request)
    success = await registry.uninstall(name)
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"status": "uninstalled", "name": name}


# ── Secret Management Endpoints ─────────────────────────────────────────────


@app.post("/api/v1/secrets", response_model=SecretResponse, status_code=201)
async def register_secret(request: Request, body: SecretRegisterRequest) -> object:
    broker = get_secret_broker(request)
    ref = broker.register_secret(
        name=body.name,
        secret_value=body.secret_value,
        description=body.description,
        expires_at=body.expires_at,
        tags=body.tags,
    )
    return {
        "credential_id": ref.credential_id,
        "name": ref.name,
        "description": ref.description,
        "created_at": ref.created_at,
        "expires_at": ref.expires_at,
        "tags": ref.tags,
    }


@app.get("/api/v1/secrets", response_model=list[SecretResponse])
async def list_secrets(request: Request) -> object:
    broker = get_secret_broker(request)
    return [
        {
            "credential_id": ref.credential_id,
            "name": ref.name,
            "description": ref.description,
            "created_at": ref.created_at,
            "expires_at": ref.expires_at,
            "tags": ref.tags,
        }
        for ref in broker.list_references()
    ]


@app.delete("/api/v1/secrets/{credential_id}")
async def revoke_secret(request: Request, credential_id: str) -> object:
    broker = get_secret_broker(request)
    success = broker.revoke_secret(credential_id)
    if not success:
        raise HTTPException(status_code=404, detail="Secret not found")
    return {"status": "revoked", "credential_id": credential_id}


# ── OAuth Endpoints ─────────────────────────────────────────────────────────


@app.post("/api/v1/integrations/oauth/authorize", response_model=OAuthAuthorizeResponse)
async def oauth_authorize(request: Request, body: OAuthAuthorizeRequest) -> object:
    manager = get_oauth_manager(request)
    try:
        auth_url, state = manager.start_authorization(
            body.provider_name,
            custom_scopes=body.custom_scopes,
            redirect_uri_override=body.redirect_uri,
        )
        return {
            "auth_url": auth_url,
            "state_token": state.state_token,
            "expires_at": state.expires_at,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/integrations/oauth/callback", response_model=OAuthTokenResponse)
async def oauth_callback(request: Request, body: OAuthCallbackRequest) -> object:
    manager = get_oauth_manager(request)
    try:
        token = await manager.exchange_code(body.provider_name, body.state_token, body.code)
        return {
            "credential_id": token.credential_id,
            "provider_name": token.provider_name,
            "token_type": token.token_type,
            "scopes": token.scopes,
            "expires_at": token.expires_at,
            "issued_at": token.issued_at,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/integrations/oauth/status", response_model=list[OAuthTokenResponse])
async def oauth_status(request: Request) -> object:
    manager = get_oauth_manager(request)
    return [
        {
            "credential_id": t.credential_id,
            "provider_name": t.provider_name,
            "token_type": t.token_type,
            "scopes": t.scopes,
            "expires_at": t.expires_at,
            "issued_at": t.issued_at,
        }
        for t in manager.list_tokens()
    ]


@app.delete("/api/v1/integrations/oauth/{provider_name}")
async def revoke_oauth_token(request: Request, provider_name: str) -> object:
    manager = get_oauth_manager(request)
    success = manager.revoke_token(provider_name)
    if not success:
        raise HTTPException(status_code=404, detail="OAuth provider token not found")
    return {"status": "revoked", "provider_name": provider_name}


# ── Capability Router Endpoints ─────────────────────────────────────────────


@app.post("/api/v1/capabilities/route", response_model=CapabilityRouteResponse)
async def route_capabilities(request: Request, body: CapabilityRouteRequest) -> object:
    router = get_capability_router(request)
    all_caps = capabilities.list()
    routed = router.route(body.query, all_caps, max_capabilities=body.max_capabilities)
    domains = sorted(router.classify_domains(body.query))
    return {
        "domains": domains,
        "capabilities": [asdict(c) for c in routed],
    }


def provenance_from_input(value: object) -> Provenance:
    data = value.model_dump()  # type: ignore[attr-defined]
    return Provenance(**data)


@app.post("/api/v1/memories", response_model=MemoryResponse, status_code=201)
async def create_memory(request: Request, body: MemoryCreateRequest) -> object:
    payload = body.model_dump(exclude={"provenance", "idempotency_key"})
    return await get_memory(request).create(
        **payload,
        provenance=provenance_from_input(body.provenance),
        dedupe_key=body.idempotency_key,
    )


@app.get("/api/v1/memories/search", response_model=list[MemoryResponse])
async def search_memories(
    request: Request,
    query: str = Query(min_length=1, max_length=10_000),
    memory_type: str | None = Query(default=None, pattern="^(semantic|episodic)$"),
    limit: int = Query(default=5, ge=1, le=50),
) -> object:
    return await get_memory(request).search(query, memory_type=memory_type, limit=limit)


@app.get("/api/v1/memories", response_model=list[MemoryResponse])
async def list_memories(request: Request, limit: int = Query(default=20, ge=1, le=50)) -> object:
    return await get_memory(request).recent(limit)


@app.get("/api/v1/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory_record(request: Request, memory_id: UUID) -> object:
    result = await get_memory(request).get(memory_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result


@app.post("/api/v1/memories/{memory_id}/correct", response_model=MemoryResponse)
async def correct_memory(request: Request, memory_id: UUID, body: MemoryCorrectRequest) -> object:
    try:
        return await get_memory(request).correct(
            memory_id,
            content=body.content,
            confidence=body.confidence,
            provenance=provenance_from_input(body.provenance),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Memory not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/api/v1/memories/{memory_id}", response_model=MemoryResponse)
async def delete_memory(request: Request, memory_id: UUID) -> object:
    try:
        return await get_memory(request).delete(memory_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Memory not found") from exc


@app.post("/api/v1/chat/messages", response_model=TaskResponse, status_code=202)
async def submit_message(request: Request, body: MessageRequest) -> object:
    runtime, runner = get_runtime(request), get_runner(request)
    task, created = await runtime.create(body.message, body.idempotency_key)
    if created:
        runner.start(UUID(task.id))
    return task


@app.post("/api/v1/chat/interactive", response_model=InteractiveChatResponse)
async def interactive_chat_endpoint(
    request: Request,
    body: InteractiveChatRequest,
) -> object:
    task_id_str = body.task_id or str(uuid4())
    if hasattr(request.app.state, "runtime"):
        runtime = cast(CeoRuntime, request.app.state.runtime)
        task_rec, _ = await runtime.create(body.message, str(uuid4()))
        task_id_str = task_rec.id

    agent = get_ceo_agent(request)
    try:
        result = await agent.run(task_id=task_id_str, objective=body.message)
    except Exception as exc:
        logger.warning("CEO agent run failed: %s", exc)
        # Return a clean 200 with an informative message instead of a 500 crash
        error_detail = str(exc)
        # Surface helpful hint for the most common config issue
        if "403" in error_detail or "401" in error_detail:
            user_msg = (
                "⚠️ I couldn't reach the AI provider — the API key is missing or invalid.\n\n"
                "**Fix**: Open your `.env` file and set:\n"
                "```\nCEO_OS_OPENROUTER_API_KEY=sk-or-v1-...\n```\n"
                "Get a free key at [openrouter.ai](https://openrouter.ai/keys). "
                "I'll use the built-in reasoning engine until then."
            )
        elif "429" in error_detail:
            user_msg = (
                "⚠️ Rate limit hit on the AI provider. I'll retry in a moment — please try again."
            )
        else:
            user_msg = f"⚠️ Execution error: {error_detail[:200]}"
        spoken = (
            user_msg.replace("**", "").replace("`", "").replace("##", "").replace("\n", " ").strip()
        )
        return {
            "task_id": task_id_str,
            "objective": body.message,
            "status": "failed",
            "thought": f"Agent error: {error_detail}",
            "final_answer": user_msg,
            "spoken_response": spoken,
            "tool_calls": [],
            "steps": [],
            "evidence": [],
            "duration_ms": 0,
        }

    # Extract tool calls and step traces
    tool_calls_list: list[dict[str, Any]] = []
    steps_list: list[dict[str, Any]] = []
    if result.trajectory:
        for s in result.trajectory.steps:
            step_dict: dict[str, Any] = {
                "step_index": s.step_index,
                "thought": s.thought,
                "tool_call": asdict(s.tool_call) if s.tool_call else None,
                "tool_response": asdict(s.tool_response) if s.tool_response else None,
                "duration_ms": s.duration_ms,
            }
            steps_list.append(step_dict)
            if s.tool_call:
                tool_calls_list.append(
                    {
                        "name": s.tool_call.name,
                        "arguments": s.tool_call.arguments,
                        "output": s.tool_response.output if s.tool_response else None,
                    }
                )

    # Update task in DB with status and output
    try:
        await tasks.update(
            UUID(task_id_str),
            status=TaskStatus.SUCCESS,
            output={
                "answer": result.final_answer,
                "thought": result.thought,
                "tools": tool_calls_list,
            },
        )
    except Exception:
        pass

    # Clean text for speech synthesis
    spoken = result.final_answer.replace("**", "").replace("`", "").replace("##", "").strip()

    return {
        "task_id": task_id_str,
        "objective": body.message,
        "status": result.status,
        "thought": result.thought,
        "final_answer": result.final_answer,
        "spoken_response": spoken,
        "tool_calls": tool_calls_list,
        "steps": steps_list,
        "evidence": result.evidence,
        "duration_ms": result.duration_ms,
    }


@app.get("/api/v1/tasks", response_model=list[TaskResponse])
async def list_tasks(limit: int = Query(50, ge=1, le=200)) -> object:
    return await tasks.list(limit)


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID) -> object:
    task = await tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def require_mutable_task(task_id: UUID) -> TaskRecord:
    task = await tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in {
        TaskStatus.SUCCESS,
        TaskStatus.PARTIAL_SUCCESS,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    }:
        raise HTTPException(status_code=409, detail=f"Task is already terminal: {task.status}")
    return task


@app.post("/api/v1/tasks/{task_id}/pause", response_model=TaskResponse)
async def pause_task(task_id: UUID) -> object:
    await require_mutable_task(task_id)
    return await tasks.set_control(task_id, TaskControl.PAUSE)


@app.post("/api/v1/tasks/{task_id}/resume", response_model=TaskResponse)
async def resume_task(task_id: UUID, request: Request) -> object:
    task = await require_mutable_task(task_id)
    if task.status != TaskStatus.WAITING:
        raise HTTPException(status_code=409, detail="Task is not paused")
    resumed = await tasks.update(task_id, control=TaskControl.RUN, status=TaskStatus.QUEUED)
    get_runner(request).start(task_id, resume=True)
    return resumed


@app.post("/api/v1/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: UUID, request: Request) -> object:
    task = await require_mutable_task(task_id)
    cancelled = await tasks.set_control(task_id, TaskControl.CANCEL)
    get_runner(request).start(task_id, resume=task.status == TaskStatus.WAITING)
    return cancelled


@app.websocket("/ws/events")
async def event_stream(websocket: WebSocket) -> None:
    await events.connect(websocket)
    try:
        await websocket.send_json({"event_type": "system.connected", "payload": {"status": "ok"}})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await events.disconnect(websocket)


async def _voice_submit(message: str) -> UUID:
    task, created = await cast(CeoRuntime, app.state.runtime).create(message)
    if created:
        cast(TaskRunner, app.state.runner).start(UUID(task.id))
    return UUID(task.id)


async def _voice_cancel(task_id: UUID) -> None:
    task = await tasks.get(task_id)
    if task is None or task.status in {
        TaskStatus.SUCCESS,
        TaskStatus.PARTIAL_SUCCESS,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    }:
        return
    await tasks.set_control(task_id, TaskControl.CANCEL)
    cast(TaskRunner, app.state.runner).start(task_id, resume=task.status == TaskStatus.WAITING)


async def _voice_wait(task_id: UUID) -> str:
    while True:
        task = await tasks.get(task_id)
        if task is None:
            return "The task could not be found."
        if task.status in {TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS}:
            return str((task.result or {}).get("message", "Completed."))
        if task.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}:
            return (
                "The task was cancelled."
                if task.status == TaskStatus.CANCELLED
                else "The task failed."
            )
        await asyncio.sleep(0.05)


@app.websocket("/ws/voice")
async def voice_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    runtime = cast(VoiceRuntime, app.state.voice)
    try:
        session = await runtime.open_session(
            websocket.send_json,
            websocket.send_bytes,
            _voice_submit,
            _voice_cancel,
            _voice_wait,
        )
    except VoicePolicyError as exc:
        await websocket.send_json({"type": "voice.unavailable", "message": str(exc)})
        await websocket.close(code=1013)
        return
    try:
        while True:
            message = await websocket.receive()
            if message.get("bytes") is not None:
                await session.append(message["bytes"])
                continue
            if message.get("text") is None:
                break
            control = json.loads(message["text"])
            if not isinstance(control, dict):
                raise VoicePolicyError("Voice control message must be an object")
            action = control.get("type")
            if action == "voice.turn.commit":
                await session.commit(replace_active=bool(control.get("replace_active", False)))
            elif action == "voice.interrupt":
                await session.interrupt()
            elif action == "voice.stop":
                await session.stop()
            elif action == "voice.resume":
                await session.resume()
            else:
                raise VoicePolicyError("Unsupported voice control message")
    except (WebSocketDisconnect, VoicePolicyError, json.JSONDecodeError) as exc:
        if not isinstance(exc, WebSocketDisconnect):
            await websocket.send_json({"type": "voice.error", "message": str(exc)})
    finally:
        await runtime.close_session(session)


# ── Telephony Endpoints ───────────────────────────────────────────────────────


def _call_to_response(record: CallRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "provider_call_id": record.provider_call_id,
        "to_number": record.to_number,
        "from_number": record.from_number,
        "objective": record.objective,
        "status": record.status.value,
        "direction": record.direction.value,
        "duration_seconds": record.duration_seconds,
        "started_at": record.started_at,
        "ended_at": record.ended_at,
        "turns": [asdict(t) for t in record.turns],
        "summary": asdict(record.summary) if record.summary else None,
        "extracted_data": record.extracted_data,
        "cost_units": record.cost_units,
        "recording_url": record.recording_url,
    }


@app.post("/api/v1/telephony/calls", response_model=CallResponse, status_code=201)
async def initiate_call(request: Request, body: CallInitiateRequest) -> object:
    telephony = get_telephony(request)
    try:
        record = await telephony.initiate_call(
            to_number=body.to_number,
            objective=body.objective,
            from_number=body.from_number,
            idempotency_key=body.idempotency_key,
        )
        return _call_to_response(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/telephony/calls", response_model=list[CallResponse])
async def list_calls(request: Request, limit: int = 50) -> object:
    telephony = get_telephony(request)
    records = await telephony.list_calls(limit)
    return [_call_to_response(r) for r in records]


@app.get("/api/v1/telephony/calls/{call_id}", response_model=CallResponse)
async def get_call(request: Request, call_id: str) -> object:
    telephony = get_telephony(request)
    record = await telephony.get_call(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call record not found")
    return _call_to_response(record)


@app.post("/api/v1/telephony/calls/{call_id}/terminate", response_model=CallResponse)
async def terminate_call(request: Request, call_id: str) -> object:
    telephony = get_telephony(request)
    try:
        record = await telephony.terminate_call(call_id)
        return _call_to_response(record)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Workflow Endpoints ───────────────────────────────────────────────────────


@app.post(
    "/api/v1/workflows/restaurant-booking",
    response_model=RestaurantBookingResponse,
    status_code=200,
)
async def book_restaurant_endpoint(request: Request, body: RestaurantBookingRequest) -> object:
    workflow = get_restaurant_workflow(request)
    req = ReservationRequest(
        restaurant_name=body.restaurant_name,
        party_size=body.party_size,
        date=body.date,
        time=body.time,
        booking_name=body.booking_name,
        location_bias=body.location_bias,
    )
    result = await workflow.execute(req)
    return asdict(result)


# ── Meta Marketing Endpoints ─────────────────────────────────────────────────


@app.get("/api/v1/meta/accounts", response_model=list[MetaAccountResponse])
async def list_meta_accounts(request: Request) -> object:
    client = get_meta(request)
    accounts = await client.list_ad_accounts()
    return [asdict(a) for a in accounts]


@app.get("/api/v1/meta/campaigns", response_model=list[MetaCampaignResponse])
async def list_meta_campaigns(
    request: Request,
    account_id: str | None = None,
    status: str | None = None,
) -> object:
    client = get_meta(request)
    campaigns = await client.list_campaigns(account_id=account_id, status_filter=status)
    return [asdict(c) for c in campaigns]


@app.post("/api/v1/meta/campaigns", response_model=MetaCampaignResponse, status_code=201)
async def create_meta_campaign(request: Request, body: MetaCampaignCreateRequest) -> object:
    client = get_meta(request)
    camp = await client.create_campaign(
        account_id=body.account_id,
        name=body.name,
        objective=body.objective,
        status=body.status,
        daily_budget=body.daily_budget,
    )
    return asdict(camp)


@app.patch("/api/v1/meta/campaigns/{campaign_id}", response_model=MetaCampaignResponse)
async def update_meta_campaign(
    request: Request, campaign_id: str, body: MetaCampaignUpdateRequest
) -> object:
    client = get_meta(request)
    try:
        camp = await client.update_campaign(
            campaign_id=campaign_id,
            name=body.name,
            status=body.status,
            daily_budget=body.daily_budget,
        )
        return asdict(camp)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/meta/adsets", response_model=list[MetaAdSetResponse])
async def list_meta_adsets(
    request: Request,
    campaign_id: str | None = None,
) -> object:
    client = get_meta(request)
    adsets = await client.list_adsets(campaign_id=campaign_id)
    return [asdict(a) for a in adsets]


@app.post("/api/v1/meta/adsets", response_model=MetaAdSetResponse, status_code=201)
async def create_meta_adset(request: Request, body: MetaAdSetCreateRequest) -> object:
    client = get_meta(request)
    adset = await client.create_adset(
        campaign_id=body.campaign_id,
        name=body.name,
        targeting=body.targeting,
        daily_budget=body.daily_budget,
        status=body.status,
    )
    return asdict(adset)


@app.get("/api/v1/meta/creatives", response_model=list[MetaCreativeResponse])
async def list_meta_creatives(
    request: Request,
    account_id: str | None = None,
) -> object:
    client = get_meta(request)
    creatives = await client.list_creatives(account_id=account_id)
    return [asdict(c) for c in creatives]


@app.post("/api/v1/meta/creatives", response_model=MetaCreativeResponse, status_code=201)
async def create_meta_creative(request: Request, body: MetaCreativeCreateRequest) -> object:
    client = get_meta(request)
    cr = await client.create_creative(
        account_id=body.account_id,
        name=body.name,
        title=body.title,
        body=body.body,
        image_url=body.image_url,
        link_url=body.link_url,
        call_to_action_type=body.call_to_action_type,
    )
    return asdict(cr)


@app.get("/api/v1/meta/ads", response_model=list[MetaAdResponse])
async def list_meta_ads(
    request: Request,
    adset_id: str | None = None,
) -> object:
    client = get_meta(request)
    ads = await client.list_ads(adset_id=adset_id)
    return [asdict(a) for a in ads]


@app.post("/api/v1/meta/ads", response_model=MetaAdResponse, status_code=201)
async def create_meta_ad(request: Request, body: MetaAdCreateRequest) -> object:
    client = get_meta(request)
    ad = await client.create_ad(
        adset_id=body.adset_id,
        name=body.name,
        creative_id=body.creative_id,
        status=body.status,
    )
    return asdict(ad)


@app.get("/api/v1/meta/insights", response_model=list[MetaInsightResponse])
async def get_meta_insights(
    request: Request,
    entity_id: str,
    entity_type: str = "campaign",
) -> object:
    client = get_meta(request)
    insights = await client.get_insights(entity_id=entity_id, entity_type=entity_type)
    return [asdict(i) for i in insights]


@app.get("/api/v1/meta/reports/{campaign_id}", response_model=MetaCampaignReportResponse)
async def get_meta_campaign_report(request: Request, campaign_id: str) -> object:
    client = get_meta(request)
    try:
        report = await client.generate_report(campaign_id)
        return asdict(report)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Marketing Intelligence Endpoints ─────────────────────────────────────────


@app.get(
    "/api/v1/intelligence/marketing/diagnose",
    response_model=ProfitDiagnosticResponse,
)
async def diagnose_marketing_profit(
    request: Request,
    date: str = "2026-08-15",
    compare_date: str = "2026-08-14",
) -> object:
    engine = get_marketing_intelligence(request)
    report = engine.diagnose_profit_change(current_date=date, previous_date=compare_date)
    return asdict(report)


@app.get(
    "/api/v1/intelligence/marketing/snapshot",
    response_model=MarketingSnapshotResponse,
)
async def get_marketing_snapshot(
    request: Request,
    date: str = "2026-08-15",
) -> object:
    engine = get_marketing_intelligence(request)
    snap = engine.get_daily_snapshot(date)
    return asdict(snap)


@app.get(
    "/api/v1/intelligence/marketing/creatives",
    response_model=list[MarketingCreativePerformanceSchema],
)
async def get_marketing_creatives(
    request: Request,
    timeframe: str = "7d",
) -> object:
    engine = get_marketing_intelligence(request)
    creatives = engine.analyze_creatives(timeframe=timeframe)
    return [asdict(c) for c in creatives]


@app.get("/api/v1/intelligence/marketing/attribution")
async def get_marketing_attribution_funnel(
    request: Request,
    date_start: str = "2026-08-01",
    date_stop: str = "2026-08-15",
) -> dict[str, Any]:
    engine = get_marketing_intelligence(request)
    return engine.get_attribution_funnel(date_start=date_start, date_stop=date_stop)


# ── Communications Endpoints ─────────────────────────────────────────────────


@app.post("/api/v1/comms/email", response_model=CommsMessageResponse, status_code=201)
async def send_email_endpoint(request: Request, body: CommsEmailSendRequest) -> object:
    comms = get_comms(request)
    priority_str = body.priority.lower()
    priority = (
        Priority(priority_str) if priority_str in Priority._value2member_map_ else Priority.NORMAL
    )
    record = await comms.send_email(
        to_email=body.to_email,
        subject=body.subject,
        body=body.body,
        name=body.name,
        template_id=body.template_id,
        template_vars=body.template_vars,
        scheduled_at=body.scheduled_at,
        priority=priority,
    )
    return asdict(record)


@app.post("/api/v1/comms/sms", response_model=CommsMessageResponse, status_code=201)
async def send_sms_endpoint(request: Request, body: CommsSmsSendRequest) -> object:
    comms = get_comms(request)
    priority_str = body.priority.lower()
    priority = (
        Priority(priority_str) if priority_str in Priority._value2member_map_ else Priority.NORMAL
    )
    record = await comms.send_sms(
        to_phone=body.to_phone,
        body=body.body,
        name=body.name,
        priority=priority,
    )
    return asdict(record)


@app.post("/api/v1/comms/whatsapp", response_model=CommsMessageResponse, status_code=201)
async def send_whatsapp_endpoint(request: Request, body: CommsWhatsappSendRequest) -> object:
    comms = get_comms(request)
    record = await comms.send_whatsapp(
        to_phone=body.to_phone,
        body=body.body,
        name=body.name,
        template_id=body.template_id,
        template_vars=body.template_vars,
    )
    return asdict(record)


@app.post(
    "/api/v1/comms/notifications",
    response_model=CommsNotificationResponse,
    status_code=201,
)
async def broadcast_notification_endpoint(
    request: Request, body: CommsNotificationBroadcastRequest
) -> object:
    comms = get_comms(request)
    channels = (
        [
            MessageChannel(c.lower())
            for c in body.channels
            if c.lower() in MessageChannel._value2member_map_
        ]
        if body.channels
        else None
    )
    record = await comms.broadcast_notification(
        title=body.title,
        message=body.message,
        severity=body.severity,
        channels=channels,
    )
    return asdict(record)


@app.post("/api/v1/comms/followups", response_model=CommsFollowupResponse, status_code=201)
async def schedule_followup_endpoint(
    request: Request, body: CommsFollowupScheduleRequest
) -> object:
    comms = get_comms(request)
    ch_str = body.channel.lower()
    channel = (
        MessageChannel(ch_str)
        if ch_str in MessageChannel._value2member_map_
        else MessageChannel.WHATSAPP
    )
    task = await comms.schedule_follow_up(
        recipient_name=body.recipient_name,
        recipient_contact=body.recipient_contact,
        channel=channel,
        objective=body.objective,
        due_date=body.due_date,
        subject=body.subject,
        cadence_step=body.cadence_step,
    )
    return asdict(task)


@app.get("/api/v1/comms/followups", response_model=list[CommsFollowupResponse])
async def list_followups_endpoint(request: Request, status: str | None = None) -> object:
    comms = get_comms(request)
    tasks = await comms.list_follow_ups(status=status)
    return [asdict(t) for t in tasks]


@app.post("/api/v1/comms/analyze")
async def analyze_conversation_endpoint(
    request: Request, body: CommsConversationAnalyzeRequest
) -> dict[str, Any]:
    comms = get_comms(request)
    return await comms.analyze_conversation(body.transcript)


@app.get("/api/v1/comms/messages", response_model=list[CommsMessageResponse])
async def list_messages_endpoint(
    request: Request, channel: str | None = None, status: str | None = None
) -> object:
    comms = get_comms(request)
    ch = (
        MessageChannel(channel.lower())
        if channel and channel.lower() in MessageChannel._value2member_map_
        else None
    )
    st = (
        MessageStatus(status.lower())
        if status and status.lower() in MessageStatus._value2member_map_
        else None
    )
    messages = await comms.list_messages(channel=ch, status=st)
    return [asdict(m) for m in messages]


# ── Business Intelligence & Executive Endpoints ──────────────────────────────


@app.get(
    "/api/v1/intelligence/business/overview",
    response_model=BusinessExecutiveOverviewResponse,
)
async def get_business_overview_endpoint(request: Request, date: str = "2026-08-16") -> object:
    biz = get_business_intelligence(request)
    overview = biz.get_executive_overview(date=date)
    return asdict(overview)


@app.get(
    "/api/v1/intelligence/business/finance",
    response_model=BusinessFinancialOverviewResponse,
)
async def get_financial_overview_endpoint(request: Request) -> object:
    biz = get_business_intelligence(request)
    fin = biz.get_financial_overview()
    return asdict(fin)


@app.get(
    "/api/v1/intelligence/business/finance/affordability",
    response_model=BusinessAffordabilityResponse,
)
async def simulate_affordability_endpoint(
    request: Request,
    proposed_spend: float = 200000.0,
    purpose: str = "advertising push",
    currency: str = "INR",
) -> object:
    biz = get_business_intelligence(request)
    sim = biz.simulate_affordability(
        proposed_spend=proposed_spend, purpose=purpose, currency=currency
    )
    return asdict(sim)


@app.get(
    "/api/v1/intelligence/business/finance/invoices",
    response_model=list[BusinessInvoiceSchema],
)
async def list_invoices_endpoint(request: Request, status: str | None = None) -> object:
    biz = get_business_intelligence(request)
    invoices = biz.list_invoices(status=status)
    return [asdict(i) for i in invoices]


@app.get(
    "/api/v1/intelligence/business/sales/pipeline",
    response_model=BusinessSalesPipelineResponse,
)
async def get_sales_pipeline_endpoint(request: Request) -> object:
    biz = get_business_intelligence(request)
    pipe = biz.get_sales_pipeline()
    return asdict(pipe)


@app.get(
    "/api/v1/intelligence/business/sales/deals",
    response_model=list[BusinessDealSchema],
)
async def list_deals_endpoint(request: Request, stage: str | None = None) -> object:
    biz = get_business_intelligence(request)
    deals = biz.list_deals(stage=stage)
    return [asdict(d) for d in deals]


@app.get(
    "/api/v1/intelligence/business/operations/health",
    response_model=BusinessOperationsHealthResponse,
)
async def get_operations_health_endpoint(request: Request) -> object:
    biz = get_business_intelligence(request)
    health = biz.get_operations_health()
    return asdict(health)


@app.get(
    "/api/v1/intelligence/business/operations/inventory",
    response_model=list[BusinessInventoryItemSchema],
)
async def list_inventory_endpoint(request: Request, low_stock_only: bool = False) -> object:
    biz = get_business_intelligence(request)
    items = biz.list_inventory(low_stock_only=low_stock_only)
    return [asdict(i) for i in items]


# ── Skills Engine Endpoints ──────────────────────────────────────────────────


@app.get("/api/v1/skills", response_model=list[SkillDefinitionResponse])
async def list_skills_endpoint(
    request: Request,
    category: str | None = None,
    enabled_only: bool = False,
    owner_agent: str | None = None,
) -> object:
    skills = get_skills(request)
    skill_defs = skills.list_skills(
        category=category, enabled_only=enabled_only, owner_agent=owner_agent
    )
    return [asdict(s) for s in skill_defs]


@app.post("/api/v1/skills", response_model=SkillDefinitionResponse, status_code=201)
async def create_skill_endpoint(request: Request, body: SkillCreateRequest) -> object:
    skills = get_skills(request)
    steps = [
        SkillStep(
            step_id=s.step_id,
            capability=s.capability,
            arguments_template=s.arguments_template,
            success_condition=s.success_condition,
            timeout_seconds=s.timeout_seconds,
            optional=s.optional,
        )
        for s in body.steps
    ]
    created = skills.create_skill(
        name=body.name,
        description=body.description,
        steps=steps,
        parameters_schema=body.parameters_schema,
        category=body.category,
        tags=body.tags,
        owner_agent=body.owner_agent,
        skill_id=body.skill_id,
    )
    return asdict(created)


@app.get("/api/v1/skills/{skill_id}", response_model=SkillDefinitionResponse)
async def get_skill_endpoint(request: Request, skill_id: str) -> object:
    skills = get_skills(request)
    try:
        skill = skills.get_skill(skill_id)
        return asdict(skill)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post(
    "/api/v1/skills/{skill_id}/execute",
    response_model=SkillExecutionResponse,
)
async def execute_skill_endpoint(
    request: Request, skill_id: str, body: SkillExecuteRequest
) -> object:
    skills = get_skills(request)
    try:
        result = await skills.execute_skill(
            skill_id=skill_id,
            inputs=body.inputs,
            capability_registry=capabilities,
        )
        return asdict(result)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@app.post("/api/v1/skills/{skill_id}/test", response_model=SkillTestResponse)
async def test_skill_endpoint(request: Request, skill_id: str, body: SkillTestRequest) -> object:
    skills = get_skills(request)
    try:
        test_res = skills.test_skill(
            skill_id=skill_id,
            mock_inputs=body.mock_inputs,
            capability_registry=capabilities,
        )
        return asdict(test_res)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post(
    "/api/v1/skills/{skill_id}/version",
    response_model=SkillDefinitionResponse,
)
async def version_skill_endpoint(
    request: Request, skill_id: str, body: SkillVersionRequest
) -> object:
    skills = get_skills(request)
    try:
        new_steps = (
            [
                SkillStep(
                    step_id=s.step_id,
                    capability=s.capability,
                    arguments_template=s.arguments_template,
                    success_condition=s.success_condition,
                    timeout_seconds=s.timeout_seconds,
                    optional=s.optional,
                )
                for s in body.new_steps
            ]
            if body.new_steps is not None
            else None
        )
        updated = skills.version_skill(
            skill_id=skill_id,
            new_version=body.new_version,
            changelog=body.changelog,
            new_steps=new_steps,
            new_description=body.new_description,
        )
        return asdict(updated)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post(
    "/api/v1/skills/{skill_id}/disable",
    response_model=SkillDefinitionResponse,
)
async def disable_skill_endpoint(
    request: Request, skill_id: str, body: SkillDisableRequest
) -> object:
    skills = get_skills(request)
    try:
        updated = skills.disable_skill(skill_id=skill_id, disabled=body.disabled)
        return asdict(updated)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


# ── API Auto-Builder Endpoints ───────────────────────────────────────────────


@app.post(
    "/api/v1/integrations/autobuilder/ingest",
    response_model=ApiBuildResponse,
    status_code=201,
)
async def autobuilder_ingest_endpoint(request: Request, body: ApiIngestRequest) -> object:
    builder = get_autobuilder(request)
    try:
        build_res, _ = await builder.ingest_and_build(
            raw_spec=body.spec,
            service_name_override=body.service_name,
            base_url_override=body.base_url,
            auth_config=body.auth_config,
            auto_register=body.auto_register,
        )
        return asdict(build_res)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@app.get(
    "/api/v1/integrations/autobuilder/integrations",
    response_model=list[ApiBuildResponse],
)
async def autobuilder_list_endpoint(request: Request) -> object:
    builder = get_autobuilder(request)
    builds = builder.list_builds()
    return [asdict(b) for b in builds]


@app.get(
    "/api/v1/integrations/autobuilder/integrations/{service_name}",
    response_model=ApiInspectResponse,
)
async def autobuilder_inspect_endpoint(request: Request, service_name: str) -> object:
    builder = get_autobuilder(request)
    try:
        spec = builder.get_api_spec(service_name)
        return asdict(spec)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post(
    "/api/v1/integrations/autobuilder/integrations/{service_name}/test",
)
async def autobuilder_test_endpoint(request: Request, service_name: str) -> object:
    builder = get_autobuilder(request)
    try:
        test_rep = await builder.test_integration(service_name)
        return asdict(test_rep)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


# ── Proactive CEO Endpoints ─────────────────────────────────────────────────


@app.post(
    "/api/v1/proactive/triggers",
    response_model=TriggerResponse,
    status_code=201,
)
async def proactive_trigger_create_endpoint(request: Request, body: TriggerCreateRequest) -> object:
    engine = get_proactive(request)
    trigger = engine.create_trigger(
        name=body.name,
        description=body.description,
        category=body.category,
        metric_key=body.metric_key,
        operator=body.operator,
        threshold=body.threshold,
        severity=body.severity,
        enabled=body.enabled,
    )
    return asdict(trigger)


@app.get(
    "/api/v1/proactive/triggers",
    response_model=list[TriggerResponse],
)
async def proactive_trigger_list_endpoint(request: Request, category: str | None = None) -> object:
    engine = get_proactive(request)
    triggers = engine.list_triggers(category=category)
    return [asdict(t) for t in triggers]


@app.post(
    "/api/v1/proactive/goals",
    response_model=GoalResponse,
    status_code=201,
)
async def proactive_goal_create_endpoint(request: Request, body: GoalCreateRequest) -> object:
    engine = get_proactive(request)
    milestones_data = [m.model_dump() for m in body.milestones]
    goal = engine.create_goal(
        title=body.title,
        description=body.description,
        category=body.category,
        target_date=body.target_date,
        milestones=milestones_data,
    )
    return asdict(goal)


@app.get(
    "/api/v1/proactive/goals",
    response_model=list[GoalResponse],
)
async def proactive_goal_list_endpoint(request: Request, category: str | None = None) -> object:
    engine = get_proactive(request)
    goals = engine.list_goals(category=category)
    return [asdict(g) for g in goals]


@app.post(
    "/api/v1/proactive/evaluate",
    response_model=ProactiveEvaluateResponse,
)
async def proactive_evaluate_endpoint(
    request: Request,
    metrics_override: dict[str, float] | None = None,
) -> object:
    engine = get_proactive(request)
    report = engine.evaluate_business_state(metrics_override)
    return asdict(report)


@app.get(
    "/api/v1/proactive/insights",
    response_model=list[ProactiveInsightResponse],
)
async def proactive_insights_endpoint(request: Request) -> object:
    engine = get_proactive(request)
    insights = engine.get_active_insights()
    if not insights:
        report = engine.evaluate_business_state()
        insights = report.insights
    return [asdict(i) for i in insights]


# ── Production Hardening Subsystem Endpoints (Phase 21) ──────────────────────────


@app.get(
    "/api/v1/production/security/audit",
    response_model=SecurityAuditResponse,
)
async def production_security_audit_endpoint(
    request: Request,
    active_secret_refs: int = 4,
) -> object:
    engine = get_production(request)
    registry: CapabilityRegistry = request.app.state.runtime.capabilities
    all_specs = registry.list()
    report = engine.audit_security(
        capabilities=all_specs,
        active_secret_refs=active_secret_refs,
        credential_leases_valid=True,
    )
    return asdict(report)


@app.get(
    "/api/v1/production/cost/overview",
    response_model=FinopsCostResponse,
)
async def production_cost_overview_endpoint(request: Request) -> object:
    engine = get_production(request)
    report = engine.get_cost_overview()
    return asdict(report)


@app.get(
    "/api/v1/production/agents/performance",
    response_model=AgentPerformanceResponse,
)
async def production_agents_performance_endpoint(request: Request) -> object:
    engine = get_production(request)
    report = engine.get_agent_performance()
    return asdict(report)


@app.post(
    "/api/v1/production/confidence/verify",
    response_model=ConfidenceVerifyResponse,
)
async def production_confidence_verify_endpoint(
    request: Request,
    body: ConfidenceVerifyRequest,
) -> object:
    engine = get_production(request)
    result = engine.verify_confidence(
        task_id=body.task_id,
        capability=body.capability,
        risk_level=body.risk_level,
        confidence_score=body.confidence_score,
        evidence=body.evidence,
        uncertainty_factors=body.uncertainty_factors,
    )
    return asdict(result)


@app.get(
    "/api/v1/production/resilience/health",
    response_model=ResilienceHealthResponse,
)
async def production_resilience_health_endpoint(request: Request) -> object:
    engine = get_production(request)
    report = engine.get_resilience_health()
    return asdict(report)


# ── Agency Agents Endpoints ──────────────────────────────────────────────────


@app.get(
    "/api/v1/agency/skills",
    response_model=AgencySkillsListResponse,
)
async def agency_skills_list_endpoint(
    request: Request,
    domain: str | None = None,
    tag: str | None = None,
) -> object:
    engine = get_agency(request)
    skills = engine.list_skills(domain=domain, tag=tag)
    items = [
        {
            "name": s.name,
            "description": s.description,
            "role": s.role,
            "domain": s.domain.value,
            "tags": s.tags,
            "critical_rules": s.critical_rules,
            "workflow_phases": s.workflow_phases,
            "allowed_capabilities": s.allowed_capabilities,
        }
        for s in skills
    ]
    return {"skills": items, "count": len(items)}


@app.get(
    "/api/v1/agency/skills/{skill_name}",
    response_model=AgencySkillSchema,
)
async def agency_skill_get_endpoint(
    request: Request,
    skill_name: str,
) -> object:
    engine = get_agency(request)
    skill = engine.get_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Agency skill '{skill_name}' not found")
    return {
        "name": skill.name,
        "description": skill.description,
        "role": skill.role,
        "domain": skill.domain.value,
        "tags": skill.tags,
        "critical_rules": skill.critical_rules,
        "workflow_phases": skill.workflow_phases,
        "allowed_capabilities": skill.allowed_capabilities,
    }


@app.post(
    "/api/v1/agency/match",
    response_model=AgencyMatchResponse,
)
async def agency_match_endpoint(
    request: Request,
    body: AgencyMatchRequest,
) -> object:
    engine = get_agency(request)
    result = engine.match_skill(body.query, top_k=body.top_k)
    matches_data = [
        {
            "skill_name": m.skill_name,
            "domain": m.domain.value,
            "relevance_score": m.relevance_score,
            "matched_keywords": m.matched_keywords,
            "rationale": m.rationale,
        }
        for m in result.matches
    ]
    best_data = (
        {
            "skill_name": result.best_match.skill_name,
            "domain": result.best_match.domain.value,
            "relevance_score": result.best_match.relevance_score,
            "matched_keywords": result.best_match.matched_keywords,
            "rationale": result.best_match.rationale,
        }
        if result.best_match
        else None
    )
    return {
        "query": result.query,
        "matches": matches_data,
        "best_match": best_data,
        "total_skills_evaluated": result.total_skills_evaluated,
        "matched_at": result.matched_at,
    }


@app.post(
    "/api/v1/agency/spawn",
    response_model=AgencySpawnResponse,
)
async def agency_spawn_endpoint(
    request: Request,
    body: AgencySpawnRequest,
) -> object:
    engine = get_agency(request)
    try:
        tmpl = engine.synthesize_agent_template(body.skill_name)
        agent_name = body.agent_name or tmpl.name
        return {
            "agent_name": agent_name,
            "template_name": tmpl.name,
            "role": tmpl.role,
            "model_class": tmpl.model_class,
            "allowed_capabilities": list(tmpl.allowed_capabilities),
            "budget": asdict(tmpl.budget),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/agency/execute",
    response_model=AgencyExecuteResponse,
)
async def agency_execute_endpoint(
    request: Request,
    body: AgencyExecuteRequest,
) -> object:
    engine = get_agency(request)
    result = engine.execute_with_skill(
        task_id=body.task_id,
        objective=body.objective,
        skill_name=body.skill_name,
        context=body.context,
    )
    return asdict(result)


# ── CEO OS Executive Agent & ReAct Reasoning Engine Endpoints ───────────────


@app.post(
    "/api/v1/ceo-agent/run",
    response_model=CeoAgentRunResponse,
)
@app.post(
    "/api/v1/hermes/run",
    response_model=HermesRunResponse,
)
async def ceo_agent_run_endpoint(
    request: Request,
    body: CeoAgentRunRequest,
) -> object:
    agent = get_ceo_agent(request)
    result = await agent.run(
        task_id=body.task_id, objective=body.objective, max_turns=body.max_turns
    )
    return {
        "run_id": result.run_id,
        "task_id": result.task_id,
        "objective": result.objective,
        "status": result.status,
        "thought": result.thought,
        "final_answer": result.final_answer,
        "evidence": result.evidence,
        "duration_ms": result.duration_ms,
    }


hermes_run_endpoint = ceo_agent_run_endpoint


@app.post(
    "/api/v1/ceo-agent/reflect",
    response_model=CeoAgentReflectResponse,
)
@app.post(
    "/api/v1/hermes/reflect",
    response_model=HermesReflectResponse,
)
async def ceo_agent_reflect_endpoint(
    request: Request,
    body: CeoAgentReflectRequest,
) -> object:
    agent = get_ceo_agent(request)
    record = agent.trajectory_store.get(body.trajectory_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Trajectory '{body.trajectory_id}' not found")
    reflection = await agent.reflective_engine.reflect(record)
    return asdict(reflection)


hermes_reflect_endpoint = ceo_agent_reflect_endpoint


@app.get(
    "/api/v1/ceo-agent/trajectories",
    response_model=CeoAgentTrajectoriesResponse,
)
@app.get(
    "/api/v1/hermes/trajectories",
    response_model=HermesTrajectoriesResponse,
)
async def ceo_agent_trajectories_endpoint(request: Request) -> object:
    agent = get_ceo_agent(request)
    trajs = [asdict(t) for t in agent.trajectory_store.list_all()]
    return {"count": len(trajs), "trajectories": trajs}


hermes_trajectories_endpoint = ceo_agent_trajectories_endpoint


@app.post(
    "/api/v1/ceo-agent/subagents/spawn",
    response_model=CeoAgentSubagentSpawnResponse,
)
@app.post(
    "/api/v1/hermes/subagents/spawn",
    response_model=HermesSubagentSpawnResponse,
)
async def ceo_agent_subagent_spawn_endpoint(
    request: Request,
    body: CeoAgentSubagentSpawnRequest,
) -> object:
    agent = get_ceo_agent(request)
    spec = CeoSubagentSpec(
        subagent_id=f"sub_{uuid4().hex[:8]}",
        role=body.role,
        objective=body.objective,
        allowed_capabilities=body.allowed_capabilities,
    )
    result = await agent.swarm.spawn(spec)
    return asdict(result)


hermes_subagent_spawn_endpoint = ceo_agent_subagent_spawn_endpoint


@app.get("/api/v1/ceo-agent/status")
@app.get("/api/v1/hermes/status")
async def ceo_agent_status_endpoint(request: Request) -> object:
    agent = get_ceo_agent(request)
    trajectories = agent.trajectory_store.list_all()
    return {
        "status": "HEALTHY",
        "engine": "CEO OS Executive ReAct Reasoning Engine",
        "total_trajectories": len(trajectories),
        "capabilities_count": len(agent._get_available_capabilities()),
    }


hermes_status_endpoint = ceo_agent_status_endpoint


# ── Garry Tan's gstack Endpoints ─────────────────────────────────────────────


@app.post(
    "/api/v1/gstack/office-hours",
    response_model=GstackOfficeHoursResponse,
)
async def gstack_office_hours_endpoint(
    request: Request,
    body: GstackOfficeHoursRequest,
) -> object:
    engine = get_gstack(request)
    return asdict(engine.run_office_hours(body.idea_or_spec))


@app.post(
    "/api/v1/gstack/plan/ceo-review",
    response_model=GstackCeoReviewResponse,
)
async def gstack_ceo_review_endpoint(
    request: Request,
    body: GstackCeoReviewRequest,
) -> object:
    engine = get_gstack(request)
    return asdict(engine.run_ceo_review(body.plan_spec))


@app.post(
    "/api/v1/gstack/plan/eng-review",
    response_model=GstackEngReviewResponse,
)
async def gstack_eng_review_endpoint(
    request: Request,
    body: GstackEngReviewRequest,
) -> object:
    engine = get_gstack(request)
    return asdict(engine.run_eng_review(body.arch_spec))


@app.post(
    "/api/v1/gstack/review",
    response_model=GstackStaffReviewResponse,
)
async def gstack_staff_review_endpoint(
    request: Request,
    body: GstackStaffReviewRequest,
) -> object:
    engine = get_gstack(request)
    return asdict(engine.run_staff_review(body.files))


@app.post(
    "/api/v1/gstack/qa",
    response_model=GstackQaResponse,
)
async def gstack_qa_endpoint(
    request: Request,
    body: GstackQaRequest,
) -> object:
    engine = get_gstack(request)
    res = await engine.run_qa(routes=body.routes, base_url=body.base_url)
    return asdict(res)


@app.post(
    "/api/v1/gstack/ship",
    response_model=GstackShipResponse,
)
async def gstack_ship_endpoint(
    request: Request,
    body: GstackShipRequest,
) -> object:
    engine = get_gstack(request)
    return asdict(engine.run_ship(git_branch=body.branch, pr_title=body.pr_title))


@app.post(
    "/api/v1/gstack/pipeline",
    response_model=GstackPipelineResponse,
)
async def gstack_pipeline_endpoint(
    request: Request,
    body: GstackPipelineRequest,
) -> object:
    engine = get_gstack(request)
    res = await engine.run_full_pipeline(body.objective)
    return asdict(res)


@app.get("/api/v1/gstack/status")
async def gstack_status_endpoint(request: Request) -> object:
    del request
    return {
        "status": "HEALTHY",
        "engine": "Garry Tan gstack Virtual Engineering Suite",
        "stages": ["Think", "Plan", "Build", "Review", "Test", "Ship", "Reflect"],
        "roles": [
            "OfficeHoursPartner",
            "CeoReviewer",
            "EngineeringManager",
            "Designer",
            "StaffReviewer",
            "QaEngineer",
            "ReleaseEngineer",
        ],
    }


# ── Computer-Use Agent (CUA) Desktop Controller Endpoints ───────────────────


@app.get("/api/v1/cua/status", response_model=CuaStatusResponse)
async def cua_status_endpoint(request: Request) -> object:
    cua = get_cua(request)
    state = await cua.get_desktop_state()
    return {
        "enabled": True,
        "frontmost_app": state.frontmost_app,
        "running_apps_count": state.running_apps_count,
        "accessibility_granted": state.accessibility_granted,
        "effects_enabled": cua.controller.policy.effects_enabled,
    }


@app.get("/api/v1/cua/apps", response_model=CuaAppsResponse)
async def cua_apps_endpoint(request: Request) -> object:
    cua = get_cua(request)
    apps = await cua.list_applications()
    items = [
        {
            "bundle_id": a.bundle_id,
            "name": a.name,
            "path": a.path,
            "running": a.running,
            "frontmost": a.frontmost,
            "pid": a.pid,
        }
        for a in apps
    ]
    return {"count": len(items), "apps": items}


@app.post("/api/v1/cua/action", response_model=CuaActionResponseSchema)
async def cua_action_endpoint(request: Request, body: CuaActionRequestSchema) -> object:
    cua = get_cua(request)
    action = body.action.lower()
    if action == "focus_app":
        if not body.bundle_id:
            raise HTTPException(status_code=400, detail="bundle_id required for focus_app")
        res = await cua.focus_application(body.bundle_id)
        return {
            "action": action,
            "success": res.success,
            "output": res.output,
            "error": res.error,
        }
    elif action == "type_text":
        if not body.text:
            raise HTTPException(status_code=400, detail="text required for type_text")
        res = await cua.type_text(body.text)
        return {
            "action": action,
            "success": res.success,
            "output": res.output,
            "error": res.error,
        }
    elif action == "press_key":
        if not body.key:
            raise HTTPException(status_code=400, detail="key required for press_key")
        res = await cua.press_key(body.key, body.modifiers)
        return {
            "action": action,
            "success": res.success,
            "output": res.output,
            "error": res.error,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")


@app.post("/api/v1/cua/execute", response_model=CuaExecuteResponseSchema)
async def cua_execute_endpoint(request: Request, body: CuaExecuteRequestSchema) -> object:
    agent = get_hermes(request)
    res = await agent.run(
        task_id=f"cua_task_{int(time.time())}",
        objective=body.objective,
        max_turns=2,
    )
    return {
        "status": res.status,
        "final_answer": res.final_answer,
        "steps_count": len(res.trajectory.steps),
        "duration_ms": res.duration_ms,
    }


# ── Jarvis Voice Assistant Endpoints & WebSockets ───────────────────────────
from jarvis.backend.api.routes import router as jarvis_router  # noqa: E402
from jarvis.backend.api.websocket import ws_router as jarvis_ws_router  # noqa: E402

app.include_router(jarvis_router)
app.include_router(jarvis_router, prefix="/api/v1")
app.include_router(jarvis_ws_router)
app.include_router(jarvis_ws_router, prefix="/api/v1")
