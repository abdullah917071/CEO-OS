from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message: str
    objective: str
    status: str
    plan: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    idempotency_key: str | None
    control: str
    created_at: datetime
    updated_at: datetime


class CapabilityResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: str
    source: str


class ProvenanceInput(BaseModel):
    source_type: str = Field(min_length=1, max_length=100)
    source_uri: str | None = Field(default=None, max_length=1_000)
    source_task_id: str | None = Field(default=None, max_length=100)
    detail: str | None = Field(default=None, max_length=1_000)
    observed_at: datetime | None = None


class CreateMemoryRequest(BaseModel):
    memory_type: str = Field(pattern="^(semantic|episodic)$")
    content: str = Field(min_length=1, max_length=10_000)
    provenance: ProvenanceInput
    subject_key: str | None = Field(default=None, max_length=200)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    sensitivity: str = Field(default="internal", pattern="^(internal|confidential|restricted)$")
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)


MemoryCreateRequest = CreateMemoryRequest


class CorrectMemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    provenance: ProvenanceInput
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


MemoryCorrectRequest = CorrectMemoryRequest


class MemoryResponse(BaseModel):
    id: str
    memory_type: str
    content: str
    subject_key: str | None = None
    status: str
    confidence: float
    importance: float
    sensitivity: str
    observed_at: datetime | str
    valid_from: datetime | str
    valid_until: datetime | str | None = None
    supersedes_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    access_count: int = 0
    provenance: list[Any] = Field(default_factory=list)
    score: float | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    kind: str
    status: str
    template_name: str
    template_version: int
    parent_id: str | None
    allowed_capabilities: list[str]
    data_scope: list[str]
    model_class: str
    can_spawn_agents: bool
    max_runtime_seconds: int
    max_cost_units: int
    max_concurrency: int
    created_at: datetime
    terminated_at: datetime | None


class AgentMessageRequest(BaseModel):
    sender_id: str = Field(min_length=1, max_length=80)
    recipient_id: str = Field(min_length=1, max_length=80)
    message_type: str = Field(default="status", max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    assignment_id: str | None = Field(default=None, max_length=80)


class AgentMessageResponse(BaseModel):
    id: str
    sender_id: str
    recipient_id: str
    message_type: str
    payload: dict[str, Any]
    assignment_id: str | None
    created_at: datetime


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    template_name: str = Field(min_length=1, max_length=80)
    template_version: int = Field(default=1, ge=1)
    parent_id: str | None = Field(default=None, max_length=80)
    allowed_capabilities: list[str] = Field(default_factory=list)
    data_scope: list[str] = Field(default_factory=list)
    model_class: str = Field(default="deterministic", max_length=40)
    can_spawn_agents: bool = Field(default=False)
    max_runtime_seconds: int = Field(default=300, ge=1, le=3600)
    max_cost_units: int = Field(default=10, ge=1, le=1000)
    max_concurrency: int = Field(default=1, ge=1, le=10)


class AgentCloneRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    parent_id: str | None = Field(default=None, max_length=80)
    max_runtime_seconds: int | None = Field(default=None, ge=1, le=3600)
    max_cost_units: int | None = Field(default=None, ge=1, le=1000)
    max_concurrency: int | None = Field(default=None, ge=1, le=10)


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    role: str | None = Field(default=None, min_length=1, max_length=80)
    allowed_capabilities: list[str] | None = None
    data_scope: list[str] | None = None
    model_class: str | None = Field(default=None, max_length=40)
    can_spawn_agents: bool | None = None
    max_runtime_seconds: int | None = Field(default=None, ge=1, le=3600)
    max_cost_units: int | None = Field(default=None, ge=1, le=1000)
    max_concurrency: int | None = Field(default=None, ge=1, le=10)


class AgentAssignmentResponse(BaseModel):
    id: str
    delegation_id: str
    agent_id: str
    objective: str
    items: list[str]
    status: str
    result: dict[str, Any] | None
    evidence: list[str]
    confidence: float | None
    uncertainty: list[str]
    cost_units: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class AgentDelegationRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=10_000)
    items: list[str] = Field(min_length=1, max_length=100)
    template_name: str = Field(default="researcher", min_length=1, max_length=80)
    worker_count: int = Field(default=2, ge=1, le=10)
    context: dict[str, Any] = Field(default_factory=dict)
    max_runtime_seconds: int = Field(default=120, ge=1, le=3600)
    max_cost_units: int = Field(default=20, ge=1, le=1000)
    parent_id: str | None = Field(default=None, max_length=80)


DelegationRequest = AgentDelegationRequest


class AgentDelegationResponse(BaseModel):
    delegation_id: str
    parent_id: str
    objective: str
    status: str
    assignments: list[AgentAssignmentResponse]
    synthesized_result: dict[str, Any]
    evidence: list[str]
    confidence: float
    uncertainty: list[str]
    cost_units: int
    runtime_seconds: float
    created_at: datetime
    finished_at: datetime | None


class IntegrationStatusResponse(BaseModel):
    name: str
    version: str
    description: str
    integration_type: str
    health: str
    tool_count: int
    risk_ceiling: str
    enabled: bool
    domain: str | None = None
    connected_at: datetime | None = None
    error: str | None = None


class McpInstallRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    command: str = Field(min_length=1, max_length=255)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    domain: str = Field(default="integrations", max_length=40)
    risk_ceiling: str = Field(default="R1", pattern="^(R0|R1|R2|R3|R4)$")
    enabled: bool = True
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class SecretRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    secret_value: str = Field(min_length=1, max_length=10_000)
    description: str = Field(default="", max_length=255)
    expires_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class SecretResponse(BaseModel):
    credential_id: str
    name: str
    description: str
    created_at: datetime
    expires_at: datetime | None
    tags: list[str]


class OAuthAuthorizeRequest(BaseModel):
    provider_name: str = Field(min_length=1, max_length=80)
    custom_scopes: list[str] | None = None
    redirect_uri: str | None = None


class OAuthAuthorizeResponse(BaseModel):
    auth_url: str
    state_token: str
    expires_at: datetime


class OAuthCallbackRequest(BaseModel):
    provider_name: str = Field(min_length=1, max_length=80)
    state_token: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=1_000)


class OAuthTokenResponse(BaseModel):
    credential_id: str
    provider_name: str
    token_type: str
    scopes: list[str]
    expires_at: datetime | None
    issued_at: datetime


class CapabilityRouteRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    max_capabilities: int = Field(default=50, ge=1, le=200)


class CapabilityRouteResponse(BaseModel):
    domains: list[str]
    capabilities: list[CapabilityResponse]


# ── Telephony Schemas ────────────────────────────────────────────────────────


class CallInitiateRequest(BaseModel):
    to_number: str = Field(min_length=3, max_length=40)
    objective: str = Field(min_length=1, max_length=10_000)
    from_number: str | None = Field(default=None, max_length=40)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)


class CallTranscriptTurnSchema(BaseModel):
    speaker: str
    text: str
    timestamp_ms: int = 0
    confidence: float = 1.0


class CallSummarySchema(BaseModel):
    call_id: str
    objective_completed: bool
    summary_text: str
    action_items: list[str] = Field(default_factory=list)
    extracted_answers: dict[str, str] = Field(default_factory=dict)
    sentiment: str = "neutral"


class CallResponse(BaseModel):
    id: str
    provider_call_id: str
    to_number: str
    from_number: str
    objective: str
    status: str
    direction: str
    duration_seconds: int
    started_at: str | None = None
    ended_at: str | None = None
    turns: list[CallTranscriptTurnSchema] = Field(default_factory=list)
    summary: CallSummarySchema | None = None
    extracted_data: dict[str, str] = Field(default_factory=dict)
    cost_units: float = 0.0
    recording_url: str | None = None


# ── Workflow Schemas ─────────────────────────────────────────────────────────


class RestaurantBookingRequest(BaseModel):
    restaurant_name: str = Field(min_length=1, max_length=100)
    party_size: int = Field(default=2, ge=1, le=50)
    date: str = Field(default="today", max_length=50)
    time: str = Field(default="19:00", max_length=50)
    booking_name: str = Field(default="Abdullah", max_length=100)
    location_bias: str = Field(default="San Francisco", max_length=100)


class RestaurantBookingResponse(BaseModel):
    status: str
    restaurant_name: str
    address: str
    phone_number: str
    confirmed_time: str
    party_size: int
    booking_name: str
    call_id: str | None = None
    calendar_event_id: str | None = None
    memory_id: str | None = None
    summary: str
    evidence: list[str] = Field(default_factory=list)


# ── Meta Marketing Schemas ───────────────────────────────────────────────────


class MetaAccountResponse(BaseModel):
    id: str
    name: str
    account_status: str
    currency: str
    timezone_name: str
    amount_spent: float
    balance: float


class MetaCampaignCreateRequest(BaseModel):
    account_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    objective: str = Field(default="OUTCOME_TRAFFIC", max_length=50)
    status: str = Field(default="PAUSED", max_length=20)
    daily_budget: float | None = Field(default=None, ge=0.0)


class MetaCampaignUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    status: str | None = Field(default=None, max_length=20)
    daily_budget: float | None = Field(default=None, ge=0.0)


class MetaCampaignResponse(BaseModel):
    id: str
    account_id: str
    name: str
    objective: str
    status: str
    daily_budget: float | None = None
    lifetime_budget: float | None = None
    created_time: str = ""
    updated_time: str = ""


class MetaAdSetCreateRequest(BaseModel):
    campaign_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    targeting: dict[str, Any] = Field(default_factory=dict)
    daily_budget: float | None = Field(default=None, ge=0.0)
    status: str = Field(default="PAUSED", max_length=20)


class MetaAdSetResponse(BaseModel):
    id: str
    campaign_id: str
    name: str
    status: str
    daily_budget: float | None = None
    billing_event: str
    optimization_goal: str
    targeting: dict[str, Any] = Field(default_factory=dict)
    bid_amount: float | None = None
    start_time: str = ""
    end_time: str | None = None


class MetaCreativeCreateRequest(BaseModel):
    account_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    link_url: str | None = Field(default=None, max_length=500)
    call_to_action_type: str = Field(default="LEARN_MORE", max_length=50)


class MetaCreativeResponse(BaseModel):
    id: str
    account_id: str
    name: str
    title: str
    body: str
    image_url: str | None = None
    link_url: str | None = None
    call_to_action_type: str = "LEARN_MORE"


class MetaAdCreateRequest(BaseModel):
    adset_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    creative_id: str = Field(min_length=1, max_length=50)
    status: str = Field(default="PAUSED", max_length=20)


class MetaAdResponse(BaseModel):
    id: str
    adset_id: str
    name: str
    creative_id: str
    status: str
    created_time: str = ""


class MetaInsightResponse(BaseModel):
    entity_id: str
    entity_type: str
    date_start: str
    date_stop: str
    impressions: int
    clicks: int
    spend: float
    cpc: float
    cpm: float
    ctr: float
    conversions: int
    roas: float


class MetaCampaignReportResponse(BaseModel):
    account_id: str
    campaign_id: str
    campaign_name: str
    status: str
    daily_budget: float
    currency: str
    total_spend: float
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    conversions: int
    roas: float
    summary: str
    insights: list[MetaInsightResponse] = Field(default_factory=list)


# ── Marketing Intelligence Schemas ───────────────────────────────────────────


class MarketingAdSpendSchema(BaseModel):
    channel: str
    spend: float
    impressions: int
    clicks: int
    cpc: float
    cpm: float
    ctr: float


class MarketingTrafficSchema(BaseModel):
    sessions: int
    unique_visitors: int
    pageviews: int
    bounce_rate: float
    avg_session_duration_s: float


class MarketingCrmSchema(BaseModel):
    leads_generated: int
    mql_count: int
    sql_count: int
    pipeline_value: float
    cac: float


class MarketingSalesSchema(BaseModel):
    gross_revenue: float
    net_revenue: float
    cogs: float
    gross_profit: float
    net_profit: float
    orders_count: int
    aov: float
    refunds_amount: float
    refund_rate: float


class MarketingCreativePerformanceSchema(BaseModel):
    creative_id: str
    name: str
    channel: str
    spend: float
    conversions: int
    cpa: float
    roas: float
    fatigue_score: float
    status: str


class MarketingSnapshotResponse(BaseModel):
    date: str
    spend_by_channel: list[MarketingAdSpendSchema]
    total_spend: float
    traffic: MarketingTrafficSchema
    crm: MarketingCrmSchema
    sales: MarketingSalesSchema
    creatives: list[MarketingCreativePerformanceSchema] = Field(default_factory=list)


class ProfitDiagnosticResponse(BaseModel):
    date: str
    compare_date: str
    gross_revenue: float
    total_ad_spend: float
    net_profit: float
    profit_delta_percentage: float
    root_causes: list[str] = Field(default_factory=list)
    channel_breakdown: dict[str, Any] = Field(default_factory=dict)
    creative_fatigue_alerts: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    summary: str


# ── Communications Schemas ───────────────────────────────────────────────────


class CommsEmailSendRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    name: str | None = None
    template_id: str | None = None
    template_vars: dict[str, Any] | None = None
    scheduled_at: str | None = None
    priority: str = "normal"


class CommsSmsSendRequest(BaseModel):
    to_phone: str
    body: str
    name: str | None = None
    priority: str = "normal"


class CommsWhatsappSendRequest(BaseModel):
    to_phone: str
    body: str
    name: str | None = None
    template_id: str | None = None
    template_vars: dict[str, Any] | None = None


class CommsNotificationBroadcastRequest(BaseModel):
    title: str
    message: str
    severity: str = "info"
    channels: list[str] | None = None


class CommsFollowupScheduleRequest(BaseModel):
    recipient_name: str
    recipient_contact: str
    channel: str = "whatsapp"
    objective: str
    due_date: str
    subject: str | None = None
    cadence_step: int = 1


class CommsConversationAnalyzeRequest(BaseModel):
    transcript: str


class CommsRecipientResponse(BaseModel):
    recipient_id: str
    name: str
    email: str | None = None
    phone: str | None = None
    whatsapp_id: str | None = None


class CommsMessageResponse(BaseModel):
    message_id: str
    channel: str
    recipient: CommsRecipientResponse
    subject: str | None = None
    body: str
    template_id: str | None = None
    template_vars: dict[str, Any] = Field(default_factory=dict)
    status: str
    priority: str
    scheduled_at: str | None = None
    sent_at: str | None = None
    delivered_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommsFollowupResponse(BaseModel):
    task_id: str
    recipient: CommsRecipientResponse
    channel: str
    subject: str | None = None
    objective: str
    due_date: str
    status: str
    cadence_step: int
    extracted_tasks: list[str] = Field(default_factory=list)
    conversation_summary: str = ""


class CommsNotificationResponse(BaseModel):
    notification_id: str
    title: str
    message: str
    severity: str
    channels_dispatched: list[str] = Field(default_factory=list)
    timestamp: str


# ── Business Intelligence & Executive Schemas ────────────────────────────────


class BusinessInvoiceSchema(BaseModel):
    invoice_id: str
    client_name: str
    amount: float
    currency: str
    status: str
    due_date: str
    issued_date: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class BusinessSubscriptionSchema(BaseModel):
    subscription_id: str
    vendor: str
    category: str
    monthly_amount: float
    currency: str
    previous_amount: float
    delta_amount: float
    status: str


class BusinessFinancialOverviewResponse(BaseModel):
    cash_balance: float
    total_revenue_mtd: float
    total_expenses_mtd: float
    net_profit_mtd: float
    receivables_total: float
    receivables_overdue: float
    unpaid_invoices: list[BusinessInvoiceSchema]
    subscriptions: list[BusinessSubscriptionSchema]
    currency: str


class BusinessAffordabilityResponse(BaseModel):
    scenario: str
    proposed_spend: float
    currency: str
    affordability_verdict: str
    projected_runway_impact_months: float
    breakeven_units_or_conversions: int
    cash_buffer_remaining: float
    recommendation: str


class BusinessDealSchema(BaseModel):
    deal_id: str
    deal_name: str
    prospect_name: str
    stage: str
    value: float
    currency: str
    win_probability: float
    expected_close_date: str
    owner: str
    last_activity: str


class BusinessSalesPipelineResponse(BaseModel):
    total_deals: int
    pipeline_value: float
    weighted_value: float
    stage_breakdown: dict[str, int]
    top_deals: list[BusinessDealSchema]
    won_this_month: float
    win_rate: float


class BusinessInventoryItemSchema(BaseModel):
    sku: str
    name: str
    category: str
    stock_level: int
    reorder_point: int
    unit_cost: float
    status: str


class BusinessOrderExceptionSchema(BaseModel):
    order_id: str
    customer_name: str
    issue_type: str
    status: str
    created_at: str
    urgency: str


class BusinessOperationsHealthResponse(BaseModel):
    total_orders_today: int
    fulfillment_rate: float
    open_exceptions: list[BusinessOrderExceptionSchema]
    low_stock_items: list[BusinessInventoryItemSchema]
    refund_rate_percentage: float
    supplier_status: str


class BusinessExecutiveOverviewResponse(BaseModel):
    date: str
    headline_status: str
    revenue_growth_pct: float
    marketing_summary: str
    finance_summary: str
    sales_summary: str
    operations_summary: str
    unpaid_invoices: list[BusinessInvoiceSchema]
    subscription_alerts: list[BusinessSubscriptionSchema]
    action_items: list[str]
    summary: str


# ── Skills Engine Schemas ───────────────────────────────────────────────────


class SkillStepSchema(BaseModel):
    step_id: str
    capability: str
    arguments_template: dict[str, Any] = Field(default_factory=dict)
    success_condition: str = "Step completed"
    timeout_seconds: float = 30.0
    optional: bool = False


class SkillStatsSchema(BaseModel):
    runs_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_runtime_ms: float = 0.0
    success_rate: float = 100.0
    last_used_at: str | None = None


class SkillVersionRecordSchema(BaseModel):
    version: str
    created_at: str
    changelog: str
    steps_count: int


class SkillDefinitionResponse(BaseModel):
    skill_id: str
    name: str
    description: str
    version: str
    category: str
    tags: list[str] = Field(default_factory=list)
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    steps: list[SkillStepSchema] = Field(default_factory=list)
    owner_agent: str
    enabled: bool
    created_at: str
    updated_at: str
    stats: SkillStatsSchema
    version_history: list[SkillVersionRecordSchema] = Field(default_factory=list)


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    steps: list[SkillStepSchema]
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    owner_agent: str = "ceo"
    skill_id: str | None = None


class SkillExecuteRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class SkillExecutionResponse(BaseModel):
    execution_id: str
    skill_id: str
    status: str
    steps_executed: int
    total_steps: int
    step_outputs: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    error: str | None = None
    duration_ms: float
    executed_at: str


class SkillTestRequest(BaseModel):
    mock_inputs: dict[str, Any] = Field(default_factory=dict)


class SkillTestResponse(BaseModel):
    skill_id: str
    passed: bool
    step_results: list[dict[str, Any]] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    simulated_duration_ms: float
    tested_at: str


class SkillVersionRequest(BaseModel):
    new_version: str
    changelog: str
    new_steps: list[SkillStepSchema] | None = None
    new_description: str | None = None


class SkillDisableRequest(BaseModel):
    disabled: bool = True


# ── API Auto-Builder Schemas ────────────────────────────────────────────────


class ApiIngestRequest(BaseModel):
    spec: dict[str, Any] | str
    service_name: str | None = None
    base_url: str | None = None
    auth_config: dict[str, Any] = Field(default_factory=dict)
    auto_register: bool = True


class ApiBuildResponse(BaseModel):
    service_name: str
    title: str
    version: str
    base_url: str
    tools_generated_count: int
    tool_names: list[str]
    tests_passed: bool
    registered: bool
    created_at: str


class ApiInspectResponse(BaseModel):
    service_name: str
    title: str
    version: str
    base_url: str
    description: str
    auth_type: str
    endpoints: list[dict[str, Any]]


# ── Proactive CEO Schemas ───────────────────────────────────────────────────


class TriggerConditionSchema(BaseModel):
    metric_key: str
    operator: str
    threshold: float
    duration_days: int = 1


class TriggerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=255)
    category: str = Field(default="finance")
    metric_key: str = Field(min_length=1, max_length=80)
    operator: str = Field(default="<")
    threshold: float
    severity: str = Field(default="warning")
    enabled: bool = True


class TriggerResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    condition: TriggerConditionSchema
    severity: str
    enabled: bool
    last_checked_at: str | None = None
    last_fired_at: str | None = None
    firing_count: int = 0


class GoalMilestoneSchema(BaseModel):
    title: str
    target_value: float
    current_value: float = 0.0
    unit: str = "INR"
    target_date: str
    completed: bool = False


class GoalCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=255)
    category: str = Field(default="sales")
    target_date: str = Field(min_length=10, max_length=10)
    milestones: list[GoalMilestoneSchema] = Field(default_factory=list)


class GoalResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    target_date: str
    status: str
    progress_percentage: float
    milestones: list[GoalMilestoneSchema] = Field(default_factory=list)
    child_goals: list[str] = Field(default_factory=list)
    created_at: str


class ProactiveInsightResponse(BaseModel):
    id: str
    trigger_id: str | None
    severity: str
    title: str
    observation: str
    impact_summary: str
    recommended_action: str
    auto_action_capability: str | None = None
    auto_action_arguments: dict[str, Any] = Field(default_factory=dict)
    timestamp: str
    acknowledged: bool = False


class ProactiveEvaluateResponse(BaseModel):
    timestamp: str
    triggers_evaluated_count: int
    triggers_fired_count: int
    active_insights_count: int
    goals_tracked_count: int
    critical_alerts: list[str] = Field(default_factory=list)
    insights: list[ProactiveInsightResponse] = Field(default_factory=list)


# ── Production Hardening Subsystem (Phase 21) ───────────────────────────────────


class SecurityAuditResponse(BaseModel):
    timestamp: str
    total_capabilities_audited: int
    read_only_count: int
    harmless_write_count: int
    sensitive_business_count: int
    privileged_count: int
    secret_references_active: int
    credential_leases_valid: bool
    risk_ceiling_violations: list[str] = Field(default_factory=list)
    security_score: float
    status: str


class FinopsCostResponse(BaseModel):
    timestamp: str
    total_spend_inr: float
    currency: str = "INR"
    breakdown_by_category: dict[str, float] = Field(default_factory=dict)
    breakdown_by_agent: dict[str, float] = Field(default_factory=dict)
    tasks_processed_count: int
    unit_cost_per_task_inr: float
    detected_anomalies: list[str] = Field(default_factory=list)
    optimization_recommendations: list[str] = Field(default_factory=list)


class AgentTelemetryResponse(BaseModel):
    agent_id: str
    name: str
    domain: str
    tasks_completed: int
    tasks_failed: int
    success_rate_percentage: float
    average_runtime_ms: float
    p95_runtime_ms: float
    total_cost_inr: float
    health_status: str


class AgentPerformanceResponse(BaseModel):
    timestamp: str
    fleet_size: int
    total_tasks_completed: int
    average_fleet_success_rate: float
    average_fleet_latency_ms: float
    agent_metrics: list[AgentTelemetryResponse] = Field(default_factory=list)


class ConfidenceVerifyRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=120)
    capability: str = Field(min_length=1, max_length=120)
    risk_level: str = Field(pattern="^(r0|r1|r2|r3|r4)$")
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    uncertainty_factors: list[str] = Field(default_factory=list)


class ConfidenceVerifyResponse(BaseModel):
    task_id: str
    capability: str
    risk_level: str
    confidence_score: float
    uncertainty_factors: list[str] = Field(default_factory=list)
    gate: str
    rationale: str
    requires_human_approval: bool
    evidence_valid: bool


class ResilienceHealthResponse(BaseModel):
    timestamp: str
    retries_policy_healthy: bool
    circuit_breakers_closed: bool
    rate_limiters_operational: bool
    checkpoint_persistence_healthy: bool
    last_checkpoint_timestamp: str | None = None
    recovery_readiness_score: float
    active_alerts: list[str] = Field(default_factory=list)


# ── Agency Agents Schemas ────────────────────────────────────────────────────


class AgencySkillSchema(BaseModel):
    name: str
    description: str
    role: str
    domain: str
    tags: list[str] = Field(default_factory=list)
    critical_rules: list[str] = Field(default_factory=list)
    workflow_phases: list[str] = Field(default_factory=list)
    allowed_capabilities: list[str] = Field(default_factory=list)


class AgencySkillsListResponse(BaseModel):
    skills: list[AgencySkillSchema] = Field(default_factory=list)
    count: int


class AgencySkillMatchScoreSchema(BaseModel):
    skill_name: str
    domain: str
    relevance_score: float
    matched_keywords: list[str] = Field(default_factory=list)
    rationale: str = ""


class AgencyMatchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=20)


class AgencyMatchResponse(BaseModel):
    query: str
    matches: list[AgencySkillMatchScoreSchema] = Field(default_factory=list)
    best_match: AgencySkillMatchScoreSchema | None = None
    total_skills_evaluated: int
    matched_at: str


class AgencySpawnRequest(BaseModel):
    skill_name: str = Field(min_length=1, max_length=120)
    agent_name: str | None = None


class AgencySpawnResponse(BaseModel):
    agent_name: str
    template_name: str
    role: str
    model_class: str
    allowed_capabilities: list[str] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)


class AgencyExecuteRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=2000)
    skill_name: str | None = None
    context: dict[str, Any] | None = None


class AgencyExecuteResponse(BaseModel):
    execution_id: str
    task_id: str
    skill_name: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    quality_checks_passed: list[str] = Field(default_factory=list)
    confidence: float
    duration_ms: float
    executed_at: str


# ── CEO OS Executive Agent & ReAct Reasoning Engine Schemas ─────────────────


class CeoAgentRunRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=5000)
    max_turns: int = Field(default=6, ge=1, le=20)


class CeoAgentRunResponse(BaseModel):
    run_id: str
    task_id: str
    objective: str
    status: str
    thought: str
    final_answer: str
    evidence: list[str] = Field(default_factory=list)
    duration_ms: float


class CeoAgentReflectRequest(BaseModel):
    trajectory_id: str = Field(min_length=1, max_length=120)


class CeoAgentReflectResponse(BaseModel):
    reflection_id: str
    trajectory_id: str
    insights: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    synthesized_skill: dict[str, Any] | None = None
    evaluated_at: str


class CeoAgentTrajectoriesResponse(BaseModel):
    count: int
    trajectories: list[dict[str, Any]] = Field(default_factory=list)


class CeoAgentSubagentSpawnRequest(BaseModel):
    role: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=5000)
    allowed_capabilities: list[str] = Field(default_factory=list)


class CeoAgentSubagentSpawnResponse(BaseModel):
    subagent_id: str
    objective: str
    status: str
    output: str
    evidence: list[str] = Field(default_factory=list)
    duration_ms: float


# Backwards compatibility schema aliases
HermesRunRequest = CeoAgentRunRequest
HermesRunResponse = CeoAgentRunResponse
HermesReflectRequest = CeoAgentReflectRequest
HermesReflectResponse = CeoAgentReflectResponse
HermesTrajectoriesResponse = CeoAgentTrajectoriesResponse
HermesSubagentSpawnRequest = CeoAgentSubagentSpawnRequest
HermesSubagentSpawnResponse = CeoAgentSubagentSpawnResponse


# ── Garry Tan's gstack Schemas ───────────────────────────────────────────────


class GstackOfficeHoursRequest(BaseModel):
    idea_or_spec: str = Field(min_length=1, max_length=5000)


class GstackOfficeHoursResponse(BaseModel):
    problem_statement: str
    target_customer: str
    hair_on_fire_pain: str
    key_assumptions: list[str] = Field(default_factory=list)
    forcing_questions: list[str] = Field(default_factory=list)
    ten_star_experience: str
    verdict: str
    generated_at: str


class GstackCeoReviewRequest(BaseModel):
    plan_spec: str = Field(min_length=1, max_length=5000)


class GstackCeoReviewResponse(BaseModel):
    product_scope: str
    killer_feature: str
    scope_cuts: list[str] = Field(default_factory=list)
    strategic_differentiation: str
    verdict: str
    reviewed_at: str


class GstackEngReviewRequest(BaseModel):
    arch_spec: str = Field(min_length=1, max_length=5000)


class GstackEngReviewResponse(BaseModel):
    architecture_summary: str
    data_model_risks: list[str] = Field(default_factory=list)
    concurrency_risks: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    architectural_guardrails: list[str] = Field(default_factory=list)
    verdict: str
    reviewed_at: str


class GstackStaffReviewRequest(BaseModel):
    files: list[str] = Field(default_factory=list)


class GstackStaffReviewResponse(BaseModel):
    files_reviewed: list[str] = Field(default_factory=list)
    critical_bugs_found: list[str] = Field(default_factory=list)
    race_conditions: list[str] = Field(default_factory=list)
    security_risks: list[str] = Field(default_factory=list)
    performance_hotspots: list[str] = Field(default_factory=list)
    verdict: str
    reviewed_at: str


class GstackQaRequest(BaseModel):
    routes: list[str] | None = None
    base_url: str = "http://localhost:3000"


class GstackQaResponse(BaseModel):
    browser_checks: list[str] = Field(default_factory=list)
    routes_tested: list[str] = Field(default_factory=list)
    ui_errors: list[str] = Field(default_factory=list)
    regressions_detected: list[str] = Field(default_factory=list)
    visual_evidence: list[str] = Field(default_factory=list)
    verdict: str
    tested_at: str


class GstackShipRequest(BaseModel):
    branch: str = "main"
    pr_title: str | None = None


class GstackShipResponse(BaseModel):
    git_branch: str
    checks_passed: list[str] = Field(default_factory=list)
    commit_summary: str
    pr_title: str
    pr_body: str
    ship_status: str
    shipped_at: str


class GstackPipelineRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=5000)


class GstackPipelineResponse(BaseModel):
    run_id: str
    task_id: str
    objective: str
    current_phase: str
    office_hours: GstackOfficeHoursResponse | None = None
    ceo_review: GstackCeoReviewResponse | None = None
    eng_review: GstackEngReviewResponse | None = None
    staff_review: GstackStaffReviewResponse | None = None
    qa: GstackQaResponse | None = None
    ship: GstackShipResponse | None = None
    status: str
    total_duration_ms: float


# ── Computer-Use Agent (CUA) Desktop Controller Schemas ─────────────────────


class CuaStatusResponse(BaseModel):
    enabled: bool
    frontmost_app: str
    running_apps_count: int
    accessibility_granted: bool
    effects_enabled: bool


class CuaAppItemSchema(BaseModel):
    bundle_id: str
    name: str
    path: str
    running: bool
    frontmost: bool
    pid: int | None = None


class CuaAppsResponse(BaseModel):
    count: int
    apps: list[CuaAppItemSchema] = Field(default_factory=list)


class CuaActionRequestSchema(BaseModel):
    action: str = Field(description="Action to perform: focus_app, type_text, press_key")
    bundle_id: str | None = None
    text: str | None = None
    key: str | None = None
    modifiers: list[str] = Field(default_factory=list)


class CuaActionResponseSchema(BaseModel):
    action: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class CuaExecuteRequestSchema(BaseModel):
    objective: str = Field(min_length=1, max_length=5000)


class CuaExecuteResponseSchema(BaseModel):
    status: str
    final_answer: str
    steps_count: int
    duration_ms: float


class InteractiveChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    task_id: str | None = None
    voice_mode: bool = False


class InteractiveChatResponse(BaseModel):
    task_id: str
    objective: str
    status: str
    thought: str
    final_answer: str
    spoken_response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    duration_ms: float


# ── Universal Agent Router Schemas ─────────────────────────────────────────────


class RouterSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    division: str | None = None
    limit: int = Field(default=5, ge=1, le=50)


class RouterCandidateSchema(BaseModel):
    agent_id: str
    name: str
    role: str
    division: str
    relevance_score: float
    match_reasons: list[str] = Field(default_factory=list)
    default_tools: list[str] = Field(default_factory=list)
    score_rating: float = 5.0
    success_rate: float = 1.0


class RouterSearchResponse(BaseModel):
    query: str
    count: int
    candidates: list[RouterCandidateSchema]


class RouterDelegateRequest(BaseModel):
    agent_id: str
    task: str = Field(min_length=1, max_length=10000)
    deliverable: str = Field(default="analysis_and_plan")
    do_not_modify_production: bool = True


class RouterDelegateResponse(BaseModel):
    status: str
    agent: str
    role: str
    summary: str
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float


class RouterTeamRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=10000)
    max_specialists: int = Field(default=5, ge=1, le=20)


class RouterTeamResponse(BaseModel):
    status: str
    objective: str
    lead_agent: str
    team_size: int
    team_members: list[dict[str, Any]]
    stages_executed: int
    stage_results: list[dict[str, Any]]
    findings: list[str]
    recommendations: list[str]
    evidence: list[str]
    synthesis: str


class RouterCreateRequest(BaseModel):
    name: str
    role: str
    division: str = "general"
    mission: str
    tools: list[str] | None = None


class RouterFeedbackRequest(BaseModel):
    agent_id: str
    success: bool
    confidence: float = 0.90
    cost: float = 1.0
    rating: float | None = None
