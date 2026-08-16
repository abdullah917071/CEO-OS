"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import {
  AutomationsIcon,
  PlayIcon,
  PauseIcon,
  CheckIcon,
} from "../../components/icons";

interface AutomationRecord {
  id: string;
  name: string;
  trigger: string;
  schedule: string;
  agent: string;
  lastRun: string;
  nextRun: string;
  status: "active" | "paused";
  description: string;
}

const DEMO_AUTOMATIONS: AutomationRecord[] = [
  {
    id: "auto_morning_brief",
    name: "CEO Executive Morning Brief",
    trigger: "Scheduled Cron",
    schedule: "Every day at 08:00 IST",
    agent: "Joice (CEO Agent)",
    lastRun: "Today, 08:00",
    nextRun: "Tomorrow, 08:00",
    status: "active",
    description: "Synthesizes unread emails, calendar events, active competitor moves, and overnight repo alerts into an executive memo.",
  },
  {
    id: "auto_ci_gate",
    name: "Automated Pull Request Architecture Gate",
    trigger: "Webhook: GitHub PR Opened",
    schedule: "On-demand",
    agent: "gstack Code Reviewer",
    lastRun: "2h ago",
    nextRun: "On trigger",
    status: "active",
    description: "Runs static typecheck, security rule validation, minimal diff check, and imports verification.",
  },
  {
    id: "auto_competitor_pulse",
    name: "Weekly Competitor Pricing & Feature Pulse",
    trigger: "Scheduled Cron",
    schedule: "Every Monday at 09:00 IST",
    agent: "Pricing Analyst",
    lastRun: "3 days ago",
    nextRun: "In 4 days",
    status: "paused",
    description: "Inspects competitor websites and changelogs for new merchant tier updates and pricing changes.",
  },
];

export default function AutomationsPage() {
  const [automations, setAutomations] = useState<AutomationRecord[]>(DEMO_AUTOMATIONS);
  const [selectedAuto, setSelectedAuto] = useState<AutomationRecord | null>(DEMO_AUTOMATIONS[0]);

  const toggleStatus = (id: string) => {
    setAutomations((prev) =>
      prev.map((a) =>
        a.id === id ? { ...a, status: a.status === "active" ? "paused" : "active" } : a
      )
    );
  };

  const contextContent = selectedAuto ? (
    <>
      <div className="contextPanelHeader">
        <span>Automation Details</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{selectedAuto.id}</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-primary)", marginBottom: "4px" }}>
            {selectedAuto.name}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.5", marginBottom: "8px" }}>
            {selectedAuto.description}
          </div>
          <div style={{ display: "flex", gap: "6px" }}>
            <span className={`statusBadge ${selectedAuto.status === "active" ? "completed" : "waiting"}`}>
              {selectedAuto.status === "active" ? "Active" : "Paused"}
            </span>
          </div>
        </div>

        <div className="contextSection">
          <div className="contextSectionTitle">Trigger & Schedule</div>
          <div className="metricKeyValue">
            <span className="metricKey">Trigger Type</span>
            <span className="metricVal">{selectedAuto.trigger}</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Cadence</span>
            <span className="metricVal">{selectedAuto.schedule}</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Assigned Agent</span>
            <span className="metricVal">{selectedAuto.agent}</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Next Execution</span>
            <span className="metricVal">{selectedAuto.nextRun}</span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            style={{
              flex: 1,
              padding: "8px",
              borderRadius: "var(--radius-md)",
              background: "var(--accent-primary)",
              color: "#FFFFFF",
              fontSize: "12px",
              fontWeight: 600,
            }}
            onClick={() => alert(`Triggered manual run for ${selectedAuto.name}`)}
          >
            Run Now
          </button>
          <button
            type="button"
            style={{
              padding: "8px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-strong)",
              background: "var(--bg-surface)",
              color: "var(--text-primary)",
              fontSize: "12px",
              fontWeight: 500,
            }}
            onClick={() => toggleStatus(selectedAuto.id)}
          >
            {selectedAuto.status === "active" ? "Pause" : "Resume"}
          </button>
        </div>
      </div>
    </>
  ) : null;

  return (
    <AppShell currentRouteName="Automations" contextPanelContent={contextContent}>
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Automations</h1>
            <p className="pageSubtitle">
              Recurring and event-driven workflows managed autonomously by Joice.
            </p>
          </div>

          <button
            type="button"
            style={{
              padding: "6px 14px",
              borderRadius: "var(--radius-md)",
              background: "var(--accent-primary)",
              color: "#FFFFFF",
              fontSize: "13px",
              fontWeight: 600,
            }}
            onClick={() => alert("Open Joice conversation to create a new automation.")}
          >
            + New Automation
          </button>
        </div>

        <table className="cleanTable">
          <thead>
            <tr>
              <th>Automation</th>
              <th>Trigger & Schedule</th>
              <th>Owning Agent</th>
              <th>Last Run</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {automations.map((a) => (
              <tr
                key={a.id}
                onClick={() => setSelectedAuto(a)}
                style={{
                  cursor: "pointer",
                  background: selectedAuto?.id === a.id ? "var(--bg-surface-subtle)" : undefined,
                }}
              >
                <td>
                  <strong style={{ fontSize: "13px", color: "var(--text-primary)" }}>{a.name}</strong>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{a.id}</div>
                </td>
                <td>
                  <div style={{ fontSize: "13px", color: "var(--text-primary)" }}>{a.schedule}</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{a.trigger}</div>
                </td>
                <td style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{a.agent}</td>
                <td style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                  {a.lastRun}
                </td>
                <td>
                  <span className={`statusBadge ${a.status === "active" ? "completed" : "waiting"}`}>
                    {a.status === "active" ? "Active" : "Paused"}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleStatus(a.id);
                    }}
                    style={{
                      fontSize: "12px",
                      color: "var(--accent-primary)",
                      fontWeight: 500,
                    }}
                  >
                    {a.status === "active" ? "Pause" : "Resume"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
