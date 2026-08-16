"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { ActivityIcon, ChevronDownIcon, ChevronRightIcon } from "../../components/icons";

interface EventItem {
  id: string;
  timestamp: string;
  source: "Joice" | "Jarvis" | "Agents" | "Tools" | "System" | "Errors";
  title: string;
  details?: string;
  status: "success" | "running" | "failed";
}

const DEMO_EVENTS: EventItem[] = [
  {
    id: "evt_104",
    timestamp: "18:03:45",
    source: "Tools",
    title: "browser.navigate → https://www.swiggy.com/partner-with-us",
    details: "Loaded merchant onboarding page. HTTP 200 OK. Render time: 340ms.",
    status: "success",
  },
  {
    id: "evt_103",
    timestamp: "18:02:12",
    source: "Joice",
    title: "Assembled multi-agent team for Suppremo Competitor Research",
    details: "Assigned Pricing Analyst, Sentiment Auditor, and Research Lead.",
    status: "success",
  },
  {
    id: "evt_102",
    timestamp: "18:00:10",
    source: "Jarvis",
    title: "openWakeWord evaluated ONNX audio frame",
    details: "Keyword 'Jarvis' detected with confidence score 0.88.",
    status: "success",
  },
  {
    id: "evt_101",
    timestamp: "17:42:15",
    source: "System",
    title: "Next.js 16 Dashboard build verification completed",
    details: "All routes compiled statically in 121ms with 0 type errors.",
    status: "success",
  },
];

export default function ActivityPage() {
  const [filter, setFilter] = useState<string>("All");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filters = ["All", "Joice", "Jarvis", "Agents", "Tools", "System", "Errors"];

  const filteredEvents = DEMO_EVENTS.filter((e) => {
    if (filter === "All") return true;
    return e.source === filter;
  });

  return (
    <AppShell currentRouteName="Activity">
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Activity & Audit Log</h1>
            <p className="pageSubtitle">
              Authoritative ledger of system events, tool invocations, and agent delegations.
            </p>
          </div>

          <div className="filterTabBar">
            {filters.map((f) => (
              <button
                key={f}
                type="button"
                className={`filterTab ${filter === f ? "active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {filteredEvents.map((evt) => (
            <div
              key={evt.id}
              onClick={() => setExpandedId(expandedId === evt.id ? null : evt.id)}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "10px 14px",
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)", width: "55px" }}>
                    {evt.timestamp}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      color: "var(--accent-primary)",
                      width: "60px",
                    }}
                  >
                    {evt.source}
                  </span>
                  <span style={{ fontSize: "13px", color: "var(--text-primary)" }}>{evt.title}</span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    {evt.id}
                  </span>
                  {expandedId === evt.id ? <ChevronDownIcon size={12} /> : <ChevronRightIcon size={12} />}
                </div>
              </div>

              {expandedId === evt.id && evt.details && (
                <div
                  style={{
                    marginTop: "8px",
                    paddingTop: "8px",
                    borderTop: "1px solid var(--border-subtle)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-secondary)",
                  }}
                >
                  {evt.details}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
