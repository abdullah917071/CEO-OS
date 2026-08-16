"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import {
  TasksIcon,
  CheckIcon,
  ChevronRightIcon,
  XIcon,
} from "../../components/icons";

interface TaskRecord {
  id: string;
  title: string;
  agent: string;
  status: "running" | "completed" | "failed" | "queued";
  started: string;
  duration: string;
  tools: string[];
  outputSummary?: string;
  timeline: { time: string; event: string }[];
}

const DEMO_TASKS: TaskRecord[] = [
  {
    id: "task_suppremo_growth",
    title: "Suppremo Competitor & Pricing Analysis",
    agent: "Joice → Pricing Analyst",
    status: "running",
    started: "18:02:10",
    duration: "04:18",
    tools: ["browser.navigate", "search.google"],
    outputSummary: "Extracted merchant commission tiers (18-24%) from Swiggy & Zomato partner portals.",
    timeline: [
      { time: "18:02:10", event: "Task created by Joice" },
      { time: "18:02:12", event: "Assembled specialist team" },
      { time: "18:03:45", event: "Navigated to merchant partner portals" },
      { time: "18:05:20", event: "Extracted commission breakdown" },
    ],
  },
  {
    id: "task_landing_page",
    title: "Build Responsive Landing Page",
    agent: "Joice → Frontend Engineer",
    status: "completed",
    started: "17:40:00",
    duration: "02:15",
    tools: ["read_file", "write_to_file", "build_runner"],
    outputSummary: "React + Tailwind hero section generated and validated.",
    timeline: [
      { time: "17:40:00", event: "Task created by Joice" },
      { time: "17:41:10", event: "Generated component structure" },
      { time: "17:42:15", event: "Build check passed with 0 errors" },
    ],
  },
  {
    id: "task_ads_spend",
    title: "Analyze Google Ads Spend Anomalies",
    agent: "Joice → Marketing Specialist",
    status: "completed",
    started: "Yesterday",
    duration: "06:30",
    tools: ["integrations.google_ads", "analytics.query"],
    outputSummary: "Cost per acquisition anomaly detected on campaign #302.",
    timeline: [
      { time: "Yesterday", event: "Analyzed 30-day conversion data" },
      { time: "Yesterday", event: "Generated executive spend summary" },
    ],
  },
];

export default function TasksPage() {
  const [filter, setFilter] = useState<"all" | "active" | "completed" | "failed">("all");
  const [selectedTask, setSelectedTask] = useState<TaskRecord | null>(DEMO_TASKS[0]);

  const filteredTasks = DEMO_TASKS.filter((t) => {
    if (filter === "active") return t.status === "running" || t.status === "queued";
    if (filter === "completed") return t.status === "completed";
    if (filter === "failed") return t.status === "failed";
    return true;
  });

  const contextContent = selectedTask ? (
    <>
      <div className="contextPanelHeader">
        <span>Task Inspector</span>
        <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
          {selectedTask.id}
        </span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div className="contextSectionTitle">Overview</div>
          <div style={{ fontWeight: 600, fontSize: "13px", color: "var(--text-primary)", marginBottom: "4px" }}>
            {selectedTask.title}
          </div>
          <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
            <span className={`statusBadge ${selectedTask.status}`}>
              {selectedTask.status}
            </span>
          </div>

          <div className="metricKeyValue">
            <span className="metricKey">Created By</span>
            <span className="metricVal">Joice (CEO)</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Assigned Agent</span>
            <span className="metricVal">{selectedTask.agent}</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Started</span>
            <span className="metricVal">{selectedTask.started}</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Duration</span>
            <span className="metricVal">{selectedTask.duration}</span>
          </div>
        </div>

        {/* Timeline */}
        <div className="contextSection">
          <div className="contextSectionTitle">Execution Timeline</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {selectedTask.timeline.map((t, idx) => (
              <div key={idx} style={{ display: "flex", gap: "8px", fontSize: "12px" }}>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)", width: "55px", flexShrink: 0 }}>
                  {t.time}
                </span>
                <span style={{ color: "var(--text-primary)" }}>{t.event}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Output */}
        {selectedTask.outputSummary && (
          <div className="contextSection">
            <div className="contextSectionTitle">Output & Results</div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              {selectedTask.outputSummary}
            </div>
          </div>
        )}
      </div>
    </>
  ) : null;

  return (
    <AppShell currentRouteName="Tasks" contextPanelContent={contextContent}>
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Tasks</h1>
            <p className="pageSubtitle">
              Authoritative task execution ledger and detailed step timelines.
            </p>
          </div>

          <div className="filterTabBar">
            <button
              type="button"
              className={`filterTab ${filter === "all" ? "active" : ""}`}
              onClick={() => setFilter("all")}
            >
              All
            </button>
            <button
              type="button"
              className={`filterTab ${filter === "active" ? "active" : ""}`}
              onClick={() => setFilter("active")}
            >
              Active
            </button>
            <button
              type="button"
              className={`filterTab ${filter === "completed" ? "active" : ""}`}
              onClick={() => setFilter("completed")}
            >
              Completed
            </button>
            <button
              type="button"
              className={`filterTab ${filter === "failed" ? "active" : ""}`}
              onClick={() => setFilter("failed")}
            >
              Failed
            </button>
          </div>
        </div>

        {/* Clean Tasks Table */}
        <table className="cleanTable">
          <thead>
            <tr>
              <th>Task</th>
              <th>Owning Agent</th>
              <th>Status</th>
              <th>Started</th>
              <th>Duration</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredTasks.map((t) => (
              <tr
                key={t.id}
                onClick={() => setSelectedTask(t)}
                style={{
                  cursor: "pointer",
                  background: selectedTask?.id === t.id ? "var(--bg-surface-subtle)" : undefined,
                }}
              >
                <td>
                  <strong style={{ fontSize: "13px", color: "var(--text-primary)" }}>{t.title}</strong>
                  <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    {t.id}
                  </div>
                </td>
                <td style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{t.agent}</td>
                <td>
                  <span className={`statusBadge ${t.status}`}>
                    {t.status}
                  </span>
                </td>
                <td style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                  {t.started}
                </td>
                <td style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                  {t.duration}
                </td>
                <td>
                  <span style={{ fontSize: "12px", color: "var(--accent-primary)", fontWeight: 500 }}>
                    Inspect →
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
