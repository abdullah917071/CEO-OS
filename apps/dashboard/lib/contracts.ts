export type TaskStep = { capability: string; success_condition: string };
export type Task = {
  id: string;
  message: string;
  objective: string;
  status: string;
  control: string;
  plan: { steps?: TaskStep[]; success_conditions?: string[] };
  result: { message?: string; evidence?: string[]; [key: string]: unknown } | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};
export type RuntimeEvent = {
  event_type: string;
  task_id: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
};
export type Memory = {
  id: string;
  memory_type: string;
  content: string;
  subject_key: string | null;
  confidence: number;
  importance: number;
  observed_at: string;
  provenance: Array<{ source_type: string; source_uri?: string | null }>;
  score?: number | null;
};
export type Capability = { name: string; description: string; risk: string; source: string };
export type Agent = {
  id: string;
  name: string;
  role: string;
  kind: string;
  status: string;
  template_name: string;
  template_version: number;
  parent_id: string | null;
  allowed_capabilities: string[];
  data_scope: string[];
  model_class: string;
  can_spawn_agents: boolean;
  max_runtime_seconds: number;
  max_cost_units: number;
  max_concurrency: number;
  created_at: string;
  terminated_at: string | null;
};
export type AgentAssignment = {
  id: string;
  delegation_id: string;
  agent_id: string;
  objective: string;
  items: string[];
  status: string;
  result: Record<string, unknown> | null;
  evidence: string[];
  confidence: number | null;
  uncertainty: string[];
  cost_units: number;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
export type IntegrationStatus = {
  name: string;
  version: string;
  description: string;
  integration_type: string;
  health: string;
  tool_count: number;
  risk_ceiling: string;
  enabled: boolean;
  domain?: string;
  connected_at: string | null;
  error: string | null;
};
export type SecretReference = {
  credential_id: string;
  name: string;
  description: string;
  created_at: string;
  expires_at: string | null;
  tags: string[];
};
export type OAuthTokenRecord = {
  credential_id: string;
  provider_name: string;
  token_type: string;
  scopes: string[];
  expires_at: string | null;
  issued_at: string;
};

// ── Agency Agent Contracts ──────────────────────────────────────────────────
export type AgencySkill = {
  name: string;
  description: string;
  role: string;
  domain: string;
  tags: string[];
  critical_rules: string[];
  workflow_phases: string[];
  allowed_capabilities: string[];
};
export type AgencySkillMatch = {
  skill_name: string;
  domain: string;
  relevance_score: number;
  matched_keywords: string[];
  rationale: string;
};
export type AgencyMatchResponse = {
  query: string;
  matches: AgencySkillMatch[];
  best_match: AgencySkillMatch | null;
  total_skills_evaluated: number;
  matched_at: string;
};

// ── Proactive & Intelligence Contracts ──────────────────────────────────────
export type ProactiveTrigger = {
  id: string;
  name: string;
  event_type: string;
  condition: string;
  action_template: string;
  target_agent_role: string;
  priority: string;
  cooldown_seconds: number;
  enabled: boolean;
  last_fired_at: string | null;
  fire_count: number;
};
export type ProactiveGoal = {
  id: string;
  name: string;
  description: string;
  target_metric: string;
  target_value: number;
  current_value: number;
  status: string;
  milestones: Array<{ name: string; target: number; completed: boolean }>;
  created_at: string;
  updated_at: string;
};
export type ProactiveInsight = {
  id: string;
  category: string;
  title: string;
  summary: string;
  confidence: number;
  impact: string;
  recommended_actions: string[];
  created_at: string;
};

// ── Production & System Telemetry ───────────────────────────────────────────
export type SecurityAuditReport = {
  audit_id: string;
  status: string;
  overall_score: number;
  capabilities_audited: number;
  r0_count: number;
  r1_count: number;
  r2_count: number;
  r3_count: number;
  r4_count: number;
  active_secret_refs: number;
  findings: string[];
  recommendations: string[];
  audited_at: string;
};
export type FinopsCostReport = {
  report_id: string;
  currency: string;
  monthly_budget: number;
  current_mtd_spend: number;
  projected_monthly_spend: number;
  top_cost_drivers: Array<{ category: string; spend: number; percent_of_total: number }>;
  waste_identified: number;
  optimization_actions: string[];
  generated_at: string;
};
export type ResilienceHealthReport = {
  status: string;
  health_score: number;
  circuit_breakers_active: number;
  rate_limit_capacity_percent: number;
  dead_letter_queue_size: number;
  last_recovery_checkpoint: string;
  active_leases: number;
  checked_at: string;
};

// ── Hermes AI Agent Contracts ────────────────────────────────────────────────
export type HermesTrajectoryStep = {
  step_index: number;
  thought: string;
  tool_call: { name: string; arguments: Record<string, unknown>; call_id: string } | null;
  tool_response: { name: string; output: unknown; evidence: string[]; error?: string } | null;
  duration_ms: number;
  timestamp: string;
};

export type HermesTrajectoryRecord = {
  trajectory_id: string;
  task_id: string;
  objective: string;
  system_prompt: string;
  steps: HermesTrajectoryStep[];
  final_response: string;
  total_duration_ms: number;
  status: string;
  recorded_at: string;
};

export type HermesSynthesizedSkill = {
  name: string;
  description: string;
  content_markdown: string;
  source_trajectory_id: string;
  created_at: string;
};

export type HermesReflectionResult = {
  reflection_id: string;
  trajectory_id: string;
  insights: string[];
  lessons_learned: string[];
  synthesized_skill: HermesSynthesizedSkill | null;
  evaluated_at: string;
};

export type HermesRunResponse = {
  run_id: string;
  task_id: string;
  objective: string;
  status: string;
  thought: string;
  final_answer: string;
  evidence: string[];
  duration_ms: number;
};

// ── Garry Tan's gstack Contracts ─────────────────────────────────────────────

export type GstackOfficeHoursReport = {
  problem_statement: string;
  target_customer: string;
  hair_on_fire_pain: string;
  key_assumptions: string[];
  forcing_questions: string[];
  ten_star_experience: string;
  verdict: string;
  generated_at: string;
};

export type GstackCeoReviewReport = {
  product_scope: string;
  killer_feature: string;
  scope_cuts: string[];
  strategic_differentiation: string;
  verdict: string;
  reviewed_at: string;
};

export type GstackEngReviewReport = {
  architecture_summary: string;
  data_model_risks: string[];
  concurrency_risks: string[];
  failure_modes: string[];
  architectural_guardrails: string[];
  verdict: string;
  reviewed_at: string;
};

export type GstackDesignReviewReport = {
  ux_heuristic_score: number;
  anti_ai_slop_checks: string[];
  layout_hierarchy_feedback: string;
  micro_interactions: string[];
  verdict: string;
  reviewed_at: string;
};

export type GstackStaffReviewReport = {
  files_reviewed: string[];
  critical_bugs_found: string[];
  race_conditions: string[];
  security_risks: string[];
  performance_hotspots: string[];
  verdict: string;
  reviewed_at: string;
};

export type GstackQaReport = {
  browser_checks: string[];
  routes_tested: string[];
  ui_errors: string[];
  regressions_detected: string[];
  visual_evidence: string[];
  verdict: string;
  tested_at: string;
};

export type GstackShipReport = {
  git_branch: string;
  checks_passed: string[];
  commit_summary: string;
  pr_title: string;
  pr_body: string;
  ship_status: string;
  shipped_at: string;
};

export type GstackPipelineRun = {
  run_id: string;
  task_id: string;
  objective: string;
  current_phase: string;
  office_hours: GstackOfficeHoursReport | null;
  ceo_review: GstackCeoReviewReport | null;
  eng_review: GstackEngReviewReport | null;
  staff_review: GstackStaffReviewReport | null;
  qa: GstackQaReport | null;
  ship: GstackShipReport | null;
  status: string;
  total_duration_ms: number;
};

export type InteractiveChatResponse = {
  task_id: string;
  objective: string;
  status: string;
  thought: string;
  final_answer: string;
  spoken_response: string;
  tool_calls: Array<{
    name: string;
    arguments: Record<string, unknown>;
    output?: unknown;
  }>;
  steps: Array<{
    step_index: number;
    thought: string;
    tool_call?: { name: string; arguments: Record<string, unknown> } | null;
    tool_response?: { output: unknown; evidence?: string[] } | null;
    duration_ms: number;
  }>;
  evidence: string[];
  duration_ms: number;
  safe_summary?: Record<string, unknown>;
};

// ── Chat-Centric Mission Control Contracts ──────────────────────────────────
export type ExecutionEvent = {
  id: string;
  taskId: string;
  timestamp: string;
  source: "ceo" | "agent" | "browser" | "computer" | "memory" | "tool" | "router" | "system";
  status: "running" | "success" | "failed" | "blocked" | "waiting";
  title: string;
  summary?: string;
  agentId?: string;
  agentName?: string;
  toolName?: string;
  metadata?: Record<string, unknown>;
};

export type TaskPlanStep = {
  id: string;
  title: string;
  status: "completed" | "in_progress" | "pending" | "failed";
  details?: string;
};

export type AgentActiveMember = {
  id: string;
  name: string;
  role: string;
  division?: string;
  status: "working" | "idle" | "waiting" | "completed";
  currentAction?: string;
  toolsUsed?: string[];
  progress?: number;
  lastOutput?: string;
};

export type ToolExecutionChip = {
  id: string;
  type: "browser" | "search" | "memory" | "computer" | "terminal" | "filesystem" | "tool";
  title: string;
  status: "running" | "success" | "failed";
  input?: string;
  result?: string;
  durationMs?: number;
  evidence?: string;
};

export type HumanApprovalCardData = {
  id: string;
  taskId: string;
  actionName: string;
  description: string;
  riskLevel: "R1" | "R2" | "R3" | "R4";
  targetRecipient?: string;
  subject?: string;
  commandString?: string;
  affectedPath?: string;
  status: "pending" | "approved" | "rejected";
};

export type ArtifactCardData = {
  id: string;
  title: string;
  type: "website" | "document" | "code" | "report" | "image" | "spreadsheet";
  description?: string;
  previewUrl?: string;
  screenshotUrl?: string;
  filesChanged?: number;
  additions?: number;
  deletions?: number;
  content?: string;
};

export type ConversationItem = {
  id: string;
  title: string;
  preview: string;
  updatedAt: string;
  category: "today" | "yesterday" | "previous_7_days" | "older";
  status?: "running" | "completed" | "failed" | "idle";
  activeTaskCount?: number;
};

