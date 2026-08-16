"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { BrowserIcon, PlayIcon, PauseIcon, CheckIcon } from "../../components/icons";

export default function BrowserPage() {
  const [currentUrl, setCurrentUrl] = useState("https://www.swiggy.com/partner-with-us");
  const [sessionStatus] = useState("Active");

  const visitedPages = [
    { url: "https://www.zomato.com/partner", title: "Zomato Partner Hub", status: "Extracted" },
    { url: "https://www.swiggy.com/partner-with-us", title: "Swiggy Merchant Onboarding", status: "Active" },
    { url: "https://eatclub.in", title: "EatClub Superfast Food", status: "Extracted" },
    { url: "https://magicpin.in/merchant", title: "Magicpin Partner Portal", status: "Queued" },
  ];

  const recentActions = [
    { time: "18:03:12", action: "Navigate", detail: "Loaded https://www.swiggy.com/partner-with-us" },
    { time: "18:03:14", action: "Extract", detail: "Found merchant pricing table (22% base commission tier)" },
    { time: "18:03:18", action: "Screenshot", detail: "Captured full viewport for Pricing Analyst" },
  ];

  const contextContent = (
    <>
      <div className="contextPanelHeader">
        <span>Browser Telemetry</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Playwright</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div className="contextSectionTitle">Session State</div>
          <div className="metricKeyValue">
            <span className="metricKey">Engine</span>
            <span className="metricVal">Playwright Chromium</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Viewport</span>
            <span className="metricVal">1920 × 1080</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Origin Restriction</span>
            <span className="metricVal">Allowed (Read-only)</span>
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
            onClick={() => alert("Manual interactive session opened.")}
          >
            Take Control
          </button>
          <button
            type="button"
            style={{
              padding: "8px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--status-danger-border)",
              background: "var(--status-danger-bg)",
              color: "var(--status-danger-text)",
              fontSize: "12px",
              fontWeight: 600,
            }}
            onClick={() => alert("Browser automation session closed.")}
          >
            Stop
          </button>
        </div>
      </div>
    </>
  );

  return (
    <AppShell currentRouteName="Browser Automation" contextPanelContent={contextContent}>
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Browser Automation</h1>
            <p className="pageSubtitle">
              Headless browser session managed by Joice and specialist research agents.
            </p>
          </div>

          <span className="statusBadge running">● Session {sessionStatus}</span>
        </div>

        {/* Current URL Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "var(--bg-surface-subtle)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            padding: "8px 12px",
          }}
        >
          <BrowserIcon size={16} />
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--text-primary)" }}>
            {currentUrl}
          </span>
        </div>

        {/* Action Log & Visited Pages */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              padding: "14px 16px",
            }}
          >
            <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
              Visited Pages in Task
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {visitedPages.map((p, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "13px" }}>
                  <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{p.title}</span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{p.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              padding: "14px 16px",
            }}
          >
            <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
              Recent Browser Actions
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {recentActions.map((act, i) => (
                <div key={i} style={{ fontSize: "12px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{act.time} </span>
                  <strong style={{ color: "var(--accent-primary)" }}>[{act.action}]</strong>{" "}
                  <span style={{ color: "var(--text-secondary)" }}>{act.detail}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
