"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLiveState } from "../../components/dashboard-shell";
import { formatDate, requestJson } from "../../lib/api";
import type {
  AgencyMatchResponse,
  AgencySkill,
  AgencySkillMatch,
  Agent,
  AgentAssignment,
  GstackCeoReviewReport,
  GstackDesignReviewReport,
  GstackEngReviewReport,
  GstackOfficeHoursReport,
  GstackPipelineRun,
  GstackQaReport,
  GstackShipReport,
  GstackStaffReviewReport,
  HermesReflectionResult,
  HermesRunResponse,
  HermesTrajectoryRecord,
} from "../../lib/contracts";

type TabMode = "fleet" | "agency_skills" | "hermes" | "gstack" | "assignments";

export default function AgentsPage() {
  const { revision } = useLiveState();
  const [tab, setTab] = useState<TabMode>("fleet");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [assignments, setAssignments] = useState<AgentAssignment[]>([]);
  const [agencySkills, setAgencySkills] = useState<AgencySkill[]>([]);
  const [trajectories, setTrajectories] = useState<HermesTrajectoryRecord[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>("all");
  const [skillSearch, setSkillSearch] = useState<string>("");
  const [inspectSkill, setInspectSkill] = useState<AgencySkill | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Skill Matcher Tester state
  const [matchQuery, setMatchQuery] = useState("");
  const [matching, setMatching] = useState(false);
  const [matchResults, setMatchResults] = useState<AgencySkillMatch[]>([]);

  // Hermes ReAct Execution state
  const [hermesObjective, setHermesObjective] = useState("");
  const [hermesMaxTurns, setHermesMaxTurns] = useState(6);
  const [runningHermes, setRunningHermes] = useState(false);
  const [latestHermesRun, setLatestHermesRun] = useState<HermesRunResponse | null>(null);
  const [inspectTrajectory, setInspectTrajectory] = useState<HermesTrajectoryRecord | null>(null);
  const [reflectionResult, setReflectionResult] = useState<HermesReflectionResult | null>(null);

  // Garry Tan gstack Virtual Engineering state
  const [gstackObjective, setGstackObjective] = useState("");
  const [runningGstackPipeline, setRunningGstackPipeline] = useState(false);
  const [gstackPipelineResult, setGstackPipelineResult] = useState<GstackPipelineRun | null>(null);
  const [gstackActiveRole, setGstackActiveRole] = useState<string>("office_hours");
  const [gstackRoleInput, setGstackRoleInput] = useState("");
  const [runningGstackRole, setRunningGstackRole] = useState(false);
  const [gstackRoleOutput, setGstackRoleOutput] = useState<Record<string, unknown> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [agentRows, assignmentRows, skillsData, trajData] = await Promise.all([
        requestJson<Agent[]>("/api/v1/agents"),
        requestJson<AgentAssignment[]>("/api/v1/agent-assignments?limit=50"),
        requestJson<{ skills: AgencySkill[]; count: number }>("/api/v1/agency/skills"),
        requestJson<{ count: number; trajectories: HermesTrajectoryRecord[] }>(
          "/api/v1/ceo-agent/trajectories"
        ).catch(() =>
          requestJson<{ count: number; trajectories: HermesTrajectoryRecord[] }>(
            "/api/v1/hermes/trajectories"
          ).catch(() => ({ count: 0, trajectories: [] }))
        ),
      ]);
      setAgents(agentRows);
      setAssignments(assignmentRows);
      setAgencySkills(skillsData.skills || []);
      setTrajectories(trajData.trajectories || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, revision]);

  async function controlAgent(agentId: string, action: "pause" | "resume" | "terminate") {
    try {
      setError(null);
      await requestJson(`/api/v1/agents/${agentId}/${action}`, { method: "POST" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Control action failed");
    }
  }

  async function spawnAgencyAgent(skillName: string) {
    try {
      setError(null);
      setSuccessNotice(null);
      await requestJson("/api/v1/agency/spawn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: skillName }),
      });
      setSuccessNotice(`Successfully synthesized and registered template for '${skillName}'`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Spawn failed");
    }
  }

  async function runSkillMatch(e: React.FormEvent) {
    e.preventDefault();
    if (!matchQuery.trim() || matching) return;
    setMatching(true);
    setError(null);
    try {
      const res = await requestJson<AgencyMatchResponse>("/api/v1/agency/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: matchQuery.trim(), top_k: 5 }),
      });
      setMatchResults(res.matches || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Matching failed");
    } finally {
      setMatching(false);
    }
  }

  async function handleRunHermes(e: React.FormEvent) {
    e.preventDefault();
    if (!hermesObjective.trim() || runningHermes) return;
    setRunningHermes(true);
    setError(null);
    setLatestHermesRun(null);
    try {
      const runRes = await requestJson<HermesRunResponse>("/api/v1/ceo-agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: `task_${Date.now()}`,
          objective: hermesObjective.trim(),
          max_turns: hermesMaxTurns,
        }),
      }).catch(() =>
        requestJson<HermesRunResponse>("/api/v1/hermes/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            task_id: `task_${Date.now()}`,
            objective: hermesObjective.trim(),
            max_turns: hermesMaxTurns,
          }),
        })
      );
      setLatestHermesRun(runRes);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CEO OS reasoning execution failed");
    } finally {
      setRunningHermes(false);
    }
  }

  async function handleReflect(trajectoryId: string) {
    setError(null);
    try {
      const ref = await requestJson<HermesReflectionResult>("/api/v1/ceo-agent/reflect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trajectory_id: trajectoryId }),
      }).catch(() =>
        requestJson<HermesReflectionResult>("/api/v1/hermes/reflect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ trajectory_id: trajectoryId }),
        })
      );
      setReflectionResult(ref);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reflection failed");
    }
  }

  async function runGstackPipeline(objective: string) {
    if (!objective.trim()) return;
    try {
      setRunningGstackPipeline(true);
      setError(null);
      const res = await requestJson<GstackPipelineRun>("/api/v1/gstack/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ objective: objective.trim() }),
      });
      setGstackPipelineResult(res);
      setSuccessNotice(`⚡ Garry Tan 7-stage SDLC pipeline completed in ${res.total_duration_ms.toFixed(0)}ms!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline execution failed");
    } finally {
      setRunningGstackPipeline(false);
    }
  }

  async function runGstackRole(role: string, input: string) {
    if (!input.trim()) return;
    try {
      setRunningGstackRole(true);
      setError(null);
      let endpoint = "/api/v1/gstack/office-hours";
      let payload: Record<string, unknown> = { idea_or_spec: input.trim() };

      if (role === "ceo_review") {
        endpoint = "/api/v1/gstack/plan/ceo-review";
        payload = { plan_spec: input.trim() };
      } else if (role === "eng_review") {
        endpoint = "/api/v1/gstack/plan/eng-review";
        payload = { arch_spec: input.trim() };
      } else if (role === "review") {
        endpoint = "/api/v1/gstack/review";
        payload = { files: input.split(",").map((f) => f.trim()).filter(Boolean) };
      } else if (role === "qa") {
        endpoint = "/api/v1/gstack/qa";
        payload = { routes: input.split(",").map((r) => r.trim()).filter(Boolean), base_url: "http://localhost:3000" };
      } else if (role === "ship") {
        endpoint = "/api/v1/gstack/ship";
        payload = { branch: "main", pr_title: input.trim() };
      }

      const res = await requestJson<Record<string, unknown>>(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setGstackRoleOutput(res);
      setSuccessNotice(`⚡ gstack role /${role} executed successfully!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Role execution failed");
    } finally {
      setRunningGstackRole(false);
    }
  }

  const filteredSkills = useMemo(() => {
    return agencySkills.filter((s) => {
      const matchesDomain =
        selectedDomain === "all" || s.domain.toLowerCase() === selectedDomain.toLowerCase();
      const matchesSearch =
        skillSearch === "" ||
        s.name.toLowerCase().includes(skillSearch.toLowerCase()) ||
        s.role.toLowerCase().includes(skillSearch.toLowerCase()) ||
        s.description.toLowerCase().includes(skillSearch.toLowerCase()) ||
        s.tags.some((t) => t.toLowerCase().includes(skillSearch.toLowerCase()));
      return matchesDomain && matchesSearch;
    });
  }, [agencySkills, selectedDomain, skillSearch]);

  const permanent = agents.filter((agent) => agent.kind === "permanent");
  const temporary = agents.filter((agent) => agent.kind === "temporary");
  const activeAssignments = assignments.filter((a) =>
    ["queued", "running"].includes(a.status)
  ).length;

  return (
    <>
      <section className="pageIntro">
        <p className="eyebrow">WORKFORCE & SKILLS RUNTIME</p>
        <h1>Agents & Autonomous Reasoning</h1>
        <p>
          Manage permanent leadership hierarchy, bounded temporary workers, CEO OS ReAct
          scratchpad reasoning engine, and explore 270+ specialist Agency Agent personas.
        </p>
      </section>

      {/* Telemetry Stats */}
      <div className="statGrid">
        <div className="stat highlight">
          <span>AGENCY SKILLS CATALOG</span>
          <strong>{agencySkills.length}</strong>
          <small>Specialist personas ready</small>
        </div>
        <div className="stat">
          <span>CEO REASONING TRACES</span>
          <strong>{trajectories.length}</strong>
          <small>Recorded reasoning traces</small>
        </div>
        <div className="stat">
          <span>PERMANENT FLEET</span>
          <strong>{permanent.length}</strong>
          <small>CEO & Directors</small>
        </div>
        <div className="stat">
          <span>DELEGATED ASSIGNMENTS</span>
          <strong>{activeAssignments}</strong>
          <small>Active in runtime</small>
        </div>
      </div>

      {error && <p className="notice error">CEO Error: {error}</p>}
      {successNotice && <p className="notice success">{successNotice}</p>}

      {/* Interactive Tabs */}
      <div className="tabNav">
        <button
          type="button"
          className={`tabButton ${tab === "fleet" ? "active" : ""}`}
          onClick={() => setTab("fleet")}
        >
          Active Workforce Fleet <span>({agents.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${tab === "hermes" ? "active" : ""}`}
          onClick={() => setTab("hermes")}
        >
          🧠 CEO OS ReAct Reasoning Engine <span>({trajectories.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${tab === "agency_skills" ? "active" : ""}`}
          onClick={() => setTab("agency_skills")}
        >
          270+ Agency Personas Catalog <span>({agencySkills.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${tab === "gstack" ? "active" : ""}`}
          onClick={() => setTab("gstack")}
        >
          ⚡ gstack YC Virtual Team <span>(7 Roles)</span>
        </button>
        <button
          type="button"
          className={`tabButton ${tab === "assignments" ? "active" : ""}`}
          onClick={() => setTab("assignments")}
        >
          Delegated Assignments <span>({assignments.length})</span>
        </button>
      </div>

      {/* ── TAB 1: FLEET ─────────────────────────────────────────────────── */}
      {tab === "fleet" && (
        <section className="section" style={{ marginTop: "0" }}>
          <div className="sectionTitle">
            <div>
              <p className="eyebrow">ACTIVE WORKFORCE</p>
              <h2>Hierarchy & Registered Workers</h2>
            </div>
            <span>{agents.length} agents registered</span>
          </div>

          <div className="cards agentGrid">
            {agents.map((agent) => (
              <article className={`card agentCard ${agent.kind}`} key={agent.id}>
                <div className="agentAvatar">
                  {agent.name
                    .split(" ")
                    .map((p) => p[0])
                    .join("")
                    .slice(0, 3)}
                </div>
                <div>
                  <div className="cardHead" style={{ marginBottom: "6px" }}>
                    <span
                      className={`status ${
                        agent.status === "active"
                          ? "success"
                          : agent.status === "terminated"
                          ? "cancelled"
                          : "waiting"
                      }`}
                    >
                      {agent.status}
                    </span>
                    <span style={{ fontSize: "10px", opacity: 0.6 }}>{agent.kind}</span>
                  </div>

                  <h2>{agent.name}</h2>
                  <p>
                    {agent.role} · {agent.template_name} v{agent.template_version}
                  </p>

                  <div className="tagRow">
                    <span>Model: {agent.model_class}</span>
                    <span>Max: {agent.max_runtime_seconds}s</span>
                    <span>{agent.max_cost_units} cost units</span>
                    <span>{agent.max_concurrency} max concurrency</span>
                  </div>

                  {agent.allowed_capabilities.length > 0 && (
                    <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--muted)" }}>
                      Caps: {agent.allowed_capabilities.slice(0, 4).join(", ")}
                      {agent.allowed_capabilities.length > 4 ? ` +${agent.allowed_capabilities.length - 4}` : ""}
                    </div>
                  )}

                  {agent.kind === "temporary" && agent.status !== "terminated" && (
                    <div className="controls">
                      {agent.status === "paused" ? (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => void controlAgent(agent.id, "resume")}
                        >
                          Resume
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => void controlAgent(agent.id, "pause")}
                        >
                          Pause
                        </button>
                      )}
                      <button
                        type="button"
                        className="danger"
                        onClick={() => void controlAgent(agent.id, "terminate")}
                      >
                        Terminate
                      </button>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* ── TAB 2: CEO OS REACT ENGINE & TRAJECTORIES ────────────────────── */}
      {tab === "hermes" && (
        <section className="section" style={{ marginTop: "0" }}>
          {/* Autonomous CEO OS ReAct Console */}
          <div className="card" style={{ marginBottom: "28px", borderColor: "rgba(0, 210, 255, 0.4)" }}>
            <p className="eyebrow">CEO OS EXECUTIVE AUTONOMOUS REASONING CONSOLE</p>
            <h3 style={{ margin: "6px 0 12px", font: "600 18px var(--font-sans)" }}>
              Dispatch Multi-Turn Scratchpad ReAct Reasoning Loop
            </h3>
            <form onSubmit={handleRunHermes}>
              <div style={{ display: "flex", gap: "10px", marginBottom: "12px" }}>
                <input
                  type="text"
                  style={{
                    flex: 1,
                    minHeight: "44px",
                    padding: "0 16px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border)",
                    background: "var(--bg)",
                    color: "var(--ink)",
                  }}
                  placeholder="Enter executive objective (e.g. 'Audit AWS FinOps spend and rightsize instances')..."
                  value={hermesObjective}
                  onChange={(e) => setHermesObjective(e.target.value)}
                />
                <select
                  className="filterSelect"
                  style={{ width: "130px" }}
                  value={hermesMaxTurns}
                  onChange={(e) => setHermesMaxTurns(Number(e.target.value))}
                >
                  <option value={4}>4 Max Turns</option>
                  <option value={6}>6 Max Turns</option>
                  <option value={10}>10 Max Turns</option>
                </select>
                <button type="submit" disabled={runningHermes || !hermesObjective.trim()}>
                  {runningHermes ? "REASONING..." : "DISPATCH REASONING"}
                </button>
              </div>
            </form>

            {latestHermesRun && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "16px",
                  background: "rgba(0, 210, 255, 0.05)",
                  border: "1px solid rgba(0, 210, 255, 0.2)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                <div className="cardHead">
                  <span className="status success">REASONING COMPLETE</span>
                  <span style={{ fontSize: "11px", color: "var(--cyan)" }}>
                    {latestHermesRun.duration_ms.toFixed(1)}ms
                  </span>
                </div>
                {latestHermesRun.thought && (
                  <div style={{ marginTop: "8px" }}>
                    <strong style={{ color: "var(--cyan)", fontSize: "11px", display: "block" }}>
                      🧠 Scratchpad Reasoning:
                    </strong>
                    <p style={{ margin: "4px 0", fontSize: "13px", color: "var(--ink-subtle)" }}>
                      {latestHermesRun.thought}
                    </p>
                  </div>
                )}
                <div style={{ marginTop: "10px" }}>
                  <strong style={{ color: "var(--green)", fontSize: "11px", display: "block" }}>
                    🎯 Final Answer:
                  </strong>
                  <p style={{ margin: "4px 0", fontSize: "13px", color: "var(--ink)" }}>
                    {latestHermesRun.final_answer}
                  </p>
                </div>
                {latestHermesRun.evidence.length > 0 && (
                  <div style={{ marginTop: "10px" }}>
                    <strong style={{ color: "var(--muted)", fontSize: "11px", display: "block" }}>
                      🛡 Verified Evidence:
                    </strong>
                    <ul style={{ paddingLeft: "16px", margin: "4px 0", fontSize: "12px", color: "var(--muted)" }}>
                      {latestHermesRun.evidence.map((ev, idx) => (
                        <li key={idx}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Trajectories Stream */}
          <div className="sectionTitle">
            <div>
              <p className="eyebrow">MLOPS & EVALUATION</p>
              <h2>Recorded Execution Trajectories</h2>
            </div>
            <span>{trajectories.length} trajectories</span>
          </div>

          <div className="cards">
            {trajectories.length > 0 ? (
              trajectories.map((traj) => (
                <article className="card" key={traj.trajectory_id}>
                  <div className="cardHead">
                    <span className="status success">{traj.status}</span>
                    <time>{formatDate(traj.recorded_at)}</time>
                  </div>

                  <h3 style={{ margin: "10px 0 6px" }}>{traj.objective}</h3>
                  <p style={{ color: "var(--muted)", fontSize: "13px" }}>
                    {traj.final_response.slice(0, 180)}...
                  </p>

                  <div className="tagRow">
                    <span>{traj.steps.length} reasoning steps</span>
                    <span>{traj.total_duration_ms.toFixed(1)}ms total</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px" }}>
                      ID: {traj.trajectory_id}
                    </span>
                  </div>

                  <div className="controls" style={{ marginTop: "14px" }}>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => setInspectTrajectory(traj)}
                    >
                      INSPECT STEPS
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleReflect(traj.trajectory_id)}
                    >
                      REFLECT & SYNTHESIZE SKILL
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <div className="emptyState">
                <strong>No trajectories recorded</strong>
                <p>Dispatch a Hermes directive above to record reasoning trajectories.</p>
              </div>
            )}
          </div>

          {/* Inspect Trajectory Modal */}
          {inspectTrajectory && (
            <div className="modalBackdrop" onClick={() => setInspectTrajectory(null)}>
              <div className="modalWindow" onClick={(e) => e.stopPropagation()}>
                <div className="modalHead">
                  <div>
                    <p className="eyebrow">HERMES REASONING TRACE</p>
                    <h2>{inspectTrajectory.trajectory_id}</h2>
                    <p style={{ margin: "4px 0 0", color: "var(--green)" }}>
                      {inspectTrajectory.objective}
                    </p>
                  </div>
                  <button type="button" className="closeBtn" onClick={() => setInspectTrajectory(null)}>
                    ✕
                  </button>
                </div>

                <div style={{ marginTop: "16px", display: "grid", gap: "12px" }}>
                  {inspectTrajectory.steps.map((step) => (
                    <div
                      key={step.step_index}
                      style={{
                        padding: "12px 14px",
                        background: "var(--bg)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-sm)",
                      }}
                    >
                      <div className="cardHead" style={{ marginBottom: "6px" }}>
                        <strong style={{ color: "var(--cyan)", fontSize: "12px" }}>
                          Turn #{step.step_index}
                        </strong>
                        <span style={{ fontSize: "10px", color: "var(--muted)" }}>
                          {step.duration_ms.toFixed(1)}ms
                        </span>
                      </div>
                      {step.thought && (
                        <p style={{ fontSize: "12px", color: "var(--ink-subtle)", margin: "4px 0" }}>
                          🧠 {step.thought}
                        </p>
                      )}
                      {step.tool_call && (
                        <div style={{ marginTop: "6px", fontSize: "11px", color: "var(--green)" }}>
                          ⚡ Tool: <code>{step.tool_call.name}</code> (
                          {JSON.stringify(step.tool_call.arguments)})
                        </div>
                      )}
                      {step.tool_response && (
                        <pre
                          style={{
                            marginTop: "6px",
                            padding: "8px",
                            background: "rgba(0, 0, 0, 0.4)",
                            borderRadius: "var(--radius-sm)",
                            fontSize: "10px",
                            color: "var(--muted)",
                            overflowX: "auto",
                          }}
                        >
                          {JSON.stringify(step.tool_response.output, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Reflection Result Modal */}
          {reflectionResult && (
            <div className="modalBackdrop" onClick={() => setReflectionResult(null)}>
              <div className="modalWindow" onClick={(e) => e.stopPropagation()}>
                <div className="modalHead">
                  <div>
                    <p className="eyebrow">SELF-EVOLUTION & REFLECTION</p>
                    <h2>Reflection Analysis</h2>
                  </div>
                  <button type="button" className="closeBtn" onClick={() => setReflectionResult(null)}>
                    ✕
                  </button>
                </div>

                <div style={{ marginTop: "16px" }}>
                  <strong style={{ color: "var(--cyan)", display: "block", marginBottom: "6px" }}>
                    💡 Insights:
                  </strong>
                  <ul style={{ paddingLeft: "18px", fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                    {reflectionResult.insights.map((ins, i) => (
                      <li key={i}>{ins}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ marginTop: "16px" }}>
                  <strong style={{ color: "var(--amber)", display: "block", marginBottom: "6px" }}>
                    📚 Lessons Learned:
                  </strong>
                  <ul style={{ paddingLeft: "18px", fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                    {reflectionResult.lessons_learned.map((les, i) => (
                      <li key={i}>{les}</li>
                    ))}
                  </ul>
                </div>

                {reflectionResult.synthesized_skill && (
                  <div style={{ marginTop: "20px" }}>
                    <strong style={{ color: "var(--green)", display: "block", marginBottom: "6px" }}>
                      ✨ Synthesized Reusable Skill: `{reflectionResult.synthesized_skill.name}`
                    </strong>
                    <pre
                      style={{
                        padding: "12px",
                        background: "var(--bg)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono)",
                        color: "var(--ink-subtle)",
                        maxHeight: "200px",
                        overflowY: "auto",
                      }}
                    >
                      {reflectionResult.synthesized_skill.content_markdown}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      )}

      {/* ── TAB 3: AGENCY AGENTS DIRECTORY ───────────────────────────────── */}
      {tab === "agency_skills" && (
        <section className="section" style={{ marginTop: "0" }}>
          {/* Interactive Skill Matcher Tester */}
          <div className="card" style={{ marginBottom: "28px", borderColor: "rgba(163, 255, 18, 0.3)" }}>
            <p className="eyebrow">INTERACTIVE AGENT MATCHER</p>
            <h3 style={{ margin: "6px 0 12px", font: "600 18px var(--font-sans)" }}>
              Test Intent Matching Across All 270+ Agency Personas
            </h3>
            <form onSubmit={runSkillMatch} style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
              <input
                type="text"
                style={{
                  flex: 1,
                  minHeight: "44px",
                  padding: "0 16px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border)",
                  background: "var(--bg)",
                  color: "var(--ink)",
                }}
                placeholder="Type a task intent (e.g. 'Audit cloud AWS costs', 'Design Meta ad copy', 'Refactor rust code')..."
                value={matchQuery}
                onChange={(e) => setMatchQuery(e.target.value)}
              />
              <button type="submit" disabled={matching || !matchQuery.trim()}>
                {matching ? "EVALUATING..." : "MATCH PERSONAS"}
              </button>
            </form>

            {matchResults.length > 0 && (
              <div style={{ marginTop: "20px" }}>
                <p style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>
                  Top Ranked Specialist Matches:
                </p>
                <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                  {matchResults.map((m, idx) => (
                    <div
                      key={m.skill_name}
                      style={{
                        padding: "10px 14px",
                        background: "var(--panel)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-sm)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>
                        <strong>
                          #{idx + 1} {m.skill_name}
                        </strong>
                        <span style={{ marginLeft: "10px", fontSize: "11px", color: "var(--muted)" }}>
                          ({m.domain})
                        </span>
                        <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--ink-subtle)" }}>
                          {m.rationale}
                        </p>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span className="riskBadge r0">
                          {Math.round(m.relevance_score * 100)}% Match
                        </span>
                        <button
                          type="button"
                          className="secondary"
                          style={{ minHeight: "32px", fontSize: "10px", padding: "0 10px" }}
                          onClick={() => void spawnAgencyAgent(m.skill_name)}
                        >
                          SPAWN
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Search & Domain Filter */}
          <div className="searchBar">
            <input
              type="text"
              placeholder="Search 270+ agency agent personas by name, role, keywords..."
              value={skillSearch}
              onChange={(e) => setSkillSearch(e.target.value)}
            />
            <select
              className="filterSelect"
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
            >
              <option value="all">All Domains (270+)</option>
              <option value="engineering">Engineering & Dev</option>
              <option value="finops_finance">FinOps & Finance</option>
              <option value="marketing_growth">Marketing & Growth</option>
              <option value="sales_deal_strategy">Sales & Deals</option>
              <option value="security_qa">Security & AppSec</option>
              <option value="operations_pm">Operations & PM</option>
              <option value="design_product">Design & Product</option>
              <option value="specialized_advisory">Advisory & Executive</option>
            </select>
          </div>

          {/* Skills Grid */}
          <div className="cards agentGrid">
            {filteredSkills.map((skill) => (
              <article className="card" key={skill.name}>
                <div className="cardHead">
                  <span className="riskBadge r0">{skill.domain.replace("_", " ").toUpperCase()}</span>
                  <span style={{ fontSize: "10px", color: "var(--muted)" }}>
                    {skill.critical_rules.length} Rules · {skill.workflow_phases.length} Phases
                  </span>
                </div>

                <h3 style={{ margin: "12px 0 6px", font: "600 17px var(--font-sans)" }}>
                  {skill.name}
                </h3>
                <p style={{ color: "var(--muted)", fontSize: "12px", minHeight: "36px", lineHeight: "1.4" }}>
                  {skill.description.slice(0, 140)}...
                </p>

                <div className="tagRow">
                  <span className="domainTag">{skill.role}</span>
                  {skill.tags.slice(0, 3).map((t) => (
                    <span key={t}>{t}</span>
                  ))}
                </div>

                <div className="controls" style={{ marginTop: "16px" }}>
                  <button
                    type="button"
                    className="secondary"
                    style={{ flex: 1 }}
                    onClick={() => setInspectSkill(skill)}
                  >
                    INSPECT PERSONA
                  </button>
                  <button
                    type="button"
                    style={{ flex: 1 }}
                    onClick={() => void spawnAgencyAgent(skill.name)}
                  >
                    SPAWN AGENT
                  </button>
                </div>
              </article>
            ))}
          </div>

          {/* Inspect Modal Drawer */}
          {inspectSkill && (
            <div className="modalBackdrop" onClick={() => setInspectSkill(null)}>
              <div className="modalWindow" onClick={(e) => e.stopPropagation()}>
                <div className="modalHead">
                  <div>
                    <p className="eyebrow">{inspectSkill.domain.toUpperCase()}</p>
                    <h2>{inspectSkill.name}</h2>
                    <p style={{ margin: "4px 0 0", color: "var(--green)" }}>{inspectSkill.role}</p>
                  </div>
                  <button type="button" className="closeBtn" onClick={() => setInspectSkill(null)}>
                    ✕
                  </button>
                </div>

                <p style={{ color: "var(--ink-subtle)", lineHeight: "1.6" }}>
                  {inspectSkill.description}
                </p>

                <div style={{ marginTop: "24px" }}>
                  <strong style={{ display: "block", color: "var(--red)", marginBottom: "10px" }}>
                    🚨 Critical Persona Rules:
                  </strong>
                  <ul style={{ paddingLeft: "20px", color: "var(--muted)", fontSize: "13px", lineHeight: "1.6" }}>
                    {inspectSkill.critical_rules.map((rule, idx) => (
                      <li key={idx} style={{ marginBottom: "6px" }}>
                        {rule}
                      </li>
                    ))}
                  </ul>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <strong style={{ display: "block", color: "var(--cyan)", marginBottom: "10px" }}>
                    🔄 Workflow Phases:
                  </strong>
                  <ul style={{ paddingLeft: "20px", color: "var(--muted)", fontSize: "13px", lineHeight: "1.6" }}>
                    {inspectSkill.workflow_phases.map((phase, idx) => (
                      <li key={idx} style={{ marginBottom: "6px" }}>
                        {phase}
                      </li>
                    ))}
                  </ul>
                </div>

                <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
                  <button
                    type="button"
                    style={{ width: "100%" }}
                    onClick={() => {
                      void spawnAgencyAgent(inspectSkill.name);
                      setInspectSkill(null);
                    }}
                  >
                    SPAWN & REGISTER TEMPLATE
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* ── TAB 4: GARRY TAN GSTACK VIRTUAL ENGINEERING TEAM ─────────────── */}
      {tab === "gstack" && (
        <section className="section" style={{ marginTop: "0" }}>
          <div className="sectionTitle">
            <div>
              <p className="eyebrow">YC VIRTUAL ENGINEERING TEAM</p>
              <h2>Garry Tan gstack SDLC Suite</h2>
            </div>
            <span className="badge info">7 Specialized Roles • Think → Plan → Build → Review → Test → Ship</span>
          </div>

          {/* 7-Stage Visual Lifecycle Ribbon */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
              gap: "10px",
              marginBottom: "24px",
            }}
          >
            {[
              { num: "01", name: "Think", role: "/office-hours", desc: "YC Partner Forcing Questions" },
              { num: "02", name: "Plan", role: "/plan-ceo-review", desc: "10-Star Scope Challenge" },
              { num: "03", name: "Architect", role: "/plan-eng-review", desc: "Architecture Guardrails" },
              { num: "04", name: "Design", role: "/design-review", desc: "Anti-AI-Slop Review" },
              { num: "05", name: "Review", role: "/review", desc: "Paranoid Staff Bug Hunt" },
              { num: "06", name: "Test", role: "/qa", desc: "Browser Visual QA" },
              { num: "07", name: "Ship", role: "/ship", desc: "Git Sync & PR Release" },
            ].map((stage) => (
              <div
                key={stage.num}
                className="card"
                style={{
                  padding: "14px",
                  background: "rgba(255, 255, 255, 0.02)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--accent)" }}>{stage.num}</span>
                  <span style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase" }}>{stage.name}</span>
                </div>
                <strong style={{ fontSize: "12px", display: "block", color: "var(--foreground)", fontFamily: "monospace" }}>
                  {stage.role}
                </strong>
                <p style={{ fontSize: "11px", color: "var(--muted)", margin: "4px 0 0" }}>{stage.desc}</p>
              </div>
            ))}
          </div>

          {/* Full Pipeline Runner Box */}
          <div className="card" style={{ marginBottom: "28px", padding: "24px" }}>
            <h3 style={{ margin: "0 0 8px" }}>⚡ 1-Click 7-Stage SDLC Pipeline Runner</h3>
            <p style={{ color: "var(--muted)", fontSize: "13px", margin: "0 0 16px" }}>
              Provide a high-level feature or project objective to run Garry Tan&apos;s full Think → Plan → Build → Review → Test → Ship lifecycle.
            </p>
            <div style={{ display: "flex", gap: "12px" }}>
              <input
                type="text"
                value={gstackObjective}
                onChange={(e) => setGstackObjective(e.target.value)}
                placeholder="e.g. Build Autonomous Multi-Channel Marketing Engine with Meta API"
                style={{ flex: 1 }}
              />
              <button
                type="button"
                disabled={runningGstackPipeline || !gstackObjective.trim()}
                onClick={() => void runGstackPipeline(gstackObjective)}
                style={{ whiteSpace: "nowrap" }}
              >
                {runningGstackPipeline ? "RUNNING PIPELINE..." : "EXECUTE FULL SDLC"}
              </button>
            </div>

            {/* Pipeline Results View */}
            {gstackPipelineResult && (
              <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <h4 style={{ margin: 0 }}>
                    Pipeline Execution Report: <span style={{ color: "var(--accent)" }}>{gstackPipelineResult.objective}</span>
                  </h4>
                  <span className="badge success">
                    {gstackPipelineResult.status} in {gstackPipelineResult.total_duration_ms.toFixed(0)}ms
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
                  {/* Office Hours */}
                  {gstackPipelineResult.office_hours && (
                    <div className="card" style={{ padding: "16px", background: "rgba(255, 255, 255, 0.01)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <strong>💡 Think: Office Hours</strong>
                        <span className="badge success">{gstackPipelineResult.office_hours.verdict}</span>
                      </div>
                      <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 8px" }}>
                        <strong>Customer:</strong> {gstackPipelineResult.office_hours.target_customer}
                      </p>
                      <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 8px" }}>
                        <strong>10-Star Vision:</strong> {gstackPipelineResult.office_hours.ten_star_experience}
                      </p>
                      <strong style={{ fontSize: "11px", color: "var(--foreground)" }}>Forcing Questions:</strong>
                      <ul style={{ fontSize: "11px", color: "var(--muted)", paddingLeft: "16px", margin: "4px 0 0" }}>
                        {gstackPipelineResult.office_hours.forcing_questions.slice(0, 3).map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* CEO Review */}
                  {gstackPipelineResult.ceo_review && (
                    <div className="card" style={{ padding: "16px", background: "rgba(255, 255, 255, 0.01)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <strong>🎯 Plan: CEO Review</strong>
                        <span className="badge success">{gstackPipelineResult.ceo_review.verdict}</span>
                      </div>
                      <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 8px" }}>
                        <strong>Killer Feature:</strong> {gstackPipelineResult.ceo_review.killer_feature}
                      </p>
                      <strong style={{ fontSize: "11px", color: "var(--foreground)" }}>Scope Cuts for Velocity:</strong>
                      <ul style={{ fontSize: "11px", color: "var(--muted)", paddingLeft: "16px", margin: "4px 0 0" }}>
                        {gstackPipelineResult.ceo_review.scope_cuts.map((cut, i) => (
                          <li key={i}>{cut}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Eng Review */}
                  {gstackPipelineResult.eng_review && (
                    <div className="card" style={{ padding: "16px", background: "rgba(255, 255, 255, 0.01)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <strong>🛡️ Architect: Eng Review</strong>
                        <span className="badge success">{gstackPipelineResult.eng_review.verdict}</span>
                      </div>
                      <strong style={{ fontSize: "11px", color: "var(--foreground)" }}>Architecture Guardrails:</strong>
                      <ul style={{ fontSize: "11px", color: "var(--muted)", paddingLeft: "16px", margin: "4px 0 0" }}>
                        {gstackPipelineResult.eng_review.architectural_guardrails.map((g, i) => (
                          <li key={i}>{g}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Staff Review */}
                  {gstackPipelineResult.staff_review && (
                    <div className="card" style={{ padding: "16px", background: "rgba(255, 255, 255, 0.01)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <strong>🔍 Review: Staff Audit</strong>
                        <span className="badge success">{gstackPipelineResult.staff_review.verdict}</span>
                      </div>
                      <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 6px" }}>
                        Audited {gstackPipelineResult.staff_review.files_reviewed.length} files with 0 critical bugs found.
                      </p>
                      <strong style={{ fontSize: "11px", color: "var(--foreground)" }}>Security & Concurrency:</strong>
                      <ul style={{ fontSize: "11px", color: "var(--muted)", paddingLeft: "16px", margin: "4px 0 0" }}>
                        {gstackPipelineResult.staff_review.security_risks.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* QA */}
                  {gstackPipelineResult.qa && (
                    <div className="card" style={{ padding: "16px", background: "rgba(255, 255, 255, 0.01)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <strong>🧪 Test: Browser QA</strong>
                        <span className="badge success">{gstackPipelineResult.qa.verdict}</span>
                      </div>
                      <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 6px" }}>
                        Verified {gstackPipelineResult.qa.routes_tested.length} routes via Chromium headless daemon.
                      </p>
                      <ul style={{ fontSize: "11px", color: "var(--muted)", paddingLeft: "16px", margin: "4px 0 0" }}>
                        {gstackPipelineResult.qa.visual_evidence.map((e, i) => (
                          <li key={i}>{e}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Ship */}
                  {gstackPipelineResult.ship && (
                    <div className="card" style={{ padding: "16px", background: "rgba(255, 255, 255, 0.01)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <strong>🚀 Ship: Release PR</strong>
                        <span className="badge success">{gstackPipelineResult.ship.ship_status}</span>
                      </div>
                      <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 6px" }}>
                        <strong>PR Title:</strong> {gstackPipelineResult.ship.pr_title}
                      </p>
                      <strong style={{ fontSize: "11px", color: "var(--foreground)" }}>Quality Checks:</strong>
                      <ul style={{ fontSize: "11px", color: "var(--muted)", paddingLeft: "16px", margin: "4px 0 0" }}>
                        {gstackPipelineResult.ship.checks_passed.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Individual Role Interactive Workbench */}
          <div className="card" style={{ padding: "24px" }}>
            <h3 style={{ margin: "0 0 8px" }}>Interactive Role Slash Command Workbench</h3>
            <p style={{ color: "var(--muted)", fontSize: "13px", margin: "0 0 16px" }}>
              Invoke specific Garry Tan specialist roles directly on any code, architecture plan, or product idea.
            </p>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
              {[
                { id: "office_hours", label: "💡 /office-hours", placeholder: "Product idea or feature spec..." },
                { id: "ceo_review", label: "🎯 /plan-ceo-review", placeholder: "Product plan specification..." },
                { id: "eng_review", label: "🛡️ /plan-eng-review", placeholder: "System architecture description..." },
                { id: "review", label: "🔍 /review", placeholder: "File paths (e.g. apps/api/main.py, core/runtime.py)..." },
                { id: "qa", label: "🧪 /qa", placeholder: "Routes to test (e.g. /, /tasks, /agents)..." },
                { id: "ship", label: "🚀 /ship", placeholder: "PR Title / Release objective..." },
              ].map((role) => (
                <button
                  key={role.id}
                  type="button"
                  className={gstackActiveRole === role.id ? "tabButton active" : "tabButton"}
                  style={{ fontSize: "12px", padding: "6px 12px" }}
                  onClick={() => {
                    setGstackActiveRole(role.id);
                    setGstackRoleOutput(null);
                  }}
                >
                  {role.label}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
              <input
                type="text"
                value={gstackRoleInput}
                onChange={(e) => setGstackRoleInput(e.target.value)}
                placeholder={
                  gstackActiveRole === "office_hours"
                    ? "Enter product idea for YC partner forcing questions..."
                    : gstackActiveRole === "ceo_review"
                    ? "Enter product plan for 10-star CEO review & scope challenge..."
                    : gstackActiveRole === "eng_review"
                    ? "Enter architecture spec for Engineering Manager guardrail review..."
                    : gstackActiveRole === "review"
                    ? "Enter file paths to audit: e.g. apps/api/src/ceo_os_api/main.py"
                    : gstackActiveRole === "qa"
                    ? "Enter routes to verify: e.g. /, /tasks, /agents, /settings"
                    : "Enter release PR title: e.g. feat: release autonomous agent"
                }
                style={{ flex: 1 }}
              />
              <button
                type="button"
                disabled={runningGstackRole || !gstackRoleInput.trim()}
                onClick={() => void runGstackRole(gstackActiveRole, gstackRoleInput)}
              >
                {runningGstackRole ? "INVOKING..." : `EXECUTE /${gstackActiveRole}`}
              </button>
            </div>

            {/* Output Inspector */}
            {gstackRoleOutput && (
              <div
                style={{
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "16px",
                  marginTop: "16px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                  <strong style={{ fontSize: "13px", color: "var(--accent)" }}>
                    Output: /{gstackActiveRole}
                  </strong>
                  <span className="badge success">STATUS: 200 OK</span>
                </div>
                <pre
                  style={{
                    fontFamily: "monospace",
                    fontSize: "12px",
                    color: "var(--foreground)",
                    whiteSpace: "pre-wrap",
                    margin: 0,
                    maxHeight: "350px",
                    overflowY: "auto",
                  }}
                >
                  {JSON.stringify(gstackRoleOutput, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── TAB 5: DELEGATED ASSIGNMENTS ─────────────────────────────────── */}
      {tab === "assignments" && (
        <section className="section" style={{ marginTop: "0" }}>
          <div className="sectionTitle">
            <div>
              <p className="eyebrow">DELEGATED WORKLOG</p>
              <h2>Recent Worker Assignments</h2>
            </div>
            <span>{assignments.length} assignments</span>
          </div>

          <div className="cards">
            {assignments.length ? (
              assignments.map((assignment) => (
                <article className="card assignmentCard" key={assignment.id}>
                  <div className="cardHead">
                    <span className={`status ${assignment.status}`}>{assignment.status}</span>
                    <time>{formatDate(assignment.created_at)}</time>
                  </div>

                  <h3 style={{ margin: "12px 0 6px" }}>{assignment.objective}</h3>
                  <p style={{ color: "var(--muted)", fontSize: "13px" }}>
                    {assignment.items.join(", ")}
                  </p>

                  <div className="tagRow">
                    <span>{assignment.cost_units} cost units</span>
                    <span>
                      {assignment.confidence === null
                        ? "No confidence score"
                        : `${Math.round(assignment.confidence * 100)}% confidence`}
                    </span>
                    <span>{assignment.evidence.length} evidence records</span>
                  </div>

                  {assignment.uncertainty.map((item) => (
                    <small
                      key={item}
                      style={{ display: "block", marginTop: "10px", color: "var(--amber)" }}
                    >
                      ⚠ Uncertainty: {item}
                    </small>
                  ))}

                  {assignment.error && <p className="notice error">{assignment.error}</p>}
                </article>
              ))
            ) : (
              <div className="emptyState">
                <strong>No assignments recorded</strong>
                <p>Delegate a research directive to see parallel worker assignments.</p>
              </div>
            )}
          </div>
        </section>
      )}
    </>
  );
}
