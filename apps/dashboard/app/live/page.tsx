"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AppShell } from "../../components/app-shell";
import {
  LiveIcon,
  JoiceIcon,
  JarvisIcon,
  PauseIcon,
  XIcon,
} from "../../components/icons";

interface LiveTaskNode {
  id: string;
  name: string;
  agent: string;
  role: string;
  status: "running" | "waiting" | "tool_running" | "completed";
  currentOp: string;
  tools: string[];
  elapsed: string;
  progress: number;
}

const INITIAL_LIVE_TASKS: LiveTaskNode[] = [
  {
    id: "task_suppremo_growth",
    name: "Suppremo Competitor Research & Pricing Analysis",
    agent: "Joice → Pricing Analyst",
    role: "Financial Specialist",
    status: "running",
    currentOp: "Extracting merchant commission tiers from Swiggy & Zomato partner portals",
    tools: ["browser.navigate", "search.google"],
    elapsed: "04:18",
    progress: 75,
  },
  {
    id: "task_landing_page",
    name: "Design & Validate Modern Landing Page",
    agent: "Joice → Frontend Engineer",
    role: "UI Architect",
    status: "tool_running",
    currentOp: "Validating Next.js 16 build and ESLint quality gates",
    tools: ["read_file", "build_runner"],
    elapsed: "01:42",
    progress: 90,
  },
  {
    id: "task_jarvis_ambient",
    name: "Ambient Voice & Core Audio Stream",
    agent: "Jarvis",
    role: "Voice Assistant",
    status: "running",
    currentOp: "Continuous 16kHz PCM hardware capture and openWakeWord ONNX evaluation",
    tools: ["sounddevice.stream", "openwakeword.onnx"],
    elapsed: "14:02",
    progress: 100,
  },
];

export default function LiveExecutionPage() {
  const [tasks, setTasks] = useState<LiveTaskNode[]>(INITIAL_LIVE_TASKS);

  const handleCancel = (taskId: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
  };

  const contextContent = (
    <>
      <div className="contextPanelHeader">
        <span>Resource Telemetry</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Realtime</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div className="contextSectionTitle">System Performance</div>
          <div className="metricKeyValue">
            <span className="metricKey">CPU Utilization</span>
            <span className="metricVal">14.2%</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Memory In-Use</span>
            <span className="metricVal">418 MB</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Active Subagents</span>
            <span className="metricVal">6 Total</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">WebSocket Latency</span>
            <span className="metricVal">18 ms</span>
          </div>
        </div>

        <div className="contextSection">
          <div className="contextSectionTitle">Tool Invocations (Past 1h)</div>
          <div className="metricKeyValue">
            <span className="metricKey">browser.navigate</span>
            <span className="metricVal">14 calls</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">search.google</span>
            <span className="metricVal">8 calls</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">memory.search</span>
            <span className="metricVal">12 calls</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">read_file</span>
            <span className="metricVal">31 calls</span>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <AppShell currentRouteName="Live Execution" contextPanelContent={contextContent}>
      <div className="pageContainer">
        {/* Page Header */}
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Live Execution</h1>
            <p className="pageSubtitle">
              Real-time multi-agent execution hierarchy, running subagents, and active tool operations.
            </p>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <span className="statusBadge running">
              ● {tasks.length} Operations Running
            </span>
          </div>
        </div>

        {/* Multi-Agent Tree Visualization */}
        <div
          style={{
            background: "var(--bg-surface-subtle)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "16px 20px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <div style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.04em" }}>
            Active Execution Hierarchy
          </div>

          <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", lineHeight: "1.8", color: "var(--text-primary)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-primary)", fontWeight: 600 }}>
              <JoiceIcon size={14} /> Joice (CEO Orchestrator)
            </div>
            <div style={{ paddingLeft: "16px", color: "var(--text-secondary)" }}>
              ├── <strong>Pricing Analyst:</strong> browser.navigate → swiggy.com/partner
            </div>
            <div style={{ paddingLeft: "16px", color: "var(--text-secondary)" }}>
              ├── <strong>Sentiment Auditor:</strong> browser.inspect → Google Play Store reviews
            </div>
            <div style={{ paddingLeft: "16px", color: "var(--text-secondary)" }}>
              └── <strong>Frontend Engineer:</strong> read_file → dashboard build check
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-primary)", fontWeight: 600, marginTop: "6px" }}>
              <JarvisIcon size={14} /> Jarvis (Ambient Voice & Computer Assistant)
            </div>
            <div style={{ paddingLeft: "16px", color: "var(--text-secondary)" }}>
              └── <strong>Hardware Stream:</strong> sounddevice 16kHz PCM mono · openWakeWord ONNX inference
            </div>
          </div>
        </div>

        {/* Active Tasks Grid */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {tasks.map((task) => (
            <div
              key={task.id}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                padding: "14px 18px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className="statusBadge running">● Running</span>
                  <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>{task.name}</strong>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>({task.agent})</span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                    {task.elapsed}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCancel(task.id)}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      fontSize: "12px",
                      color: "var(--status-danger-text)",
                      padding: "3px 8px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--status-danger-border)",
                      background: "var(--status-danger-bg)",
                    }}
                  >
                    <XIcon size={12} /> Cancel
                  </button>
                  <Link
                    href="/tasks"
                    style={{
                      fontSize: "12px",
                      color: "var(--accent-primary)",
                      fontWeight: 500,
                      padding: "3px 8px",
                    }}
                  >
                    Inspect →
                  </Link>
                </div>
              </div>

              <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                <strong>Current operation:</strong> {task.currentOp}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Active Tools:
                </span>
                {task.tools.map((t) => (
                  <span
                    key={t}
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      padding: "2px 6px",
                      background: "var(--bg-surface-secondary)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      color: "var(--text-primary)",
                    }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
