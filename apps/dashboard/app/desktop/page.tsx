"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { ComputerIcon, CheckIcon, PauseIcon } from "../../components/icons";

export default function DesktopPage() {
  const [activeApp] = useState("Google Chrome");
  const [currentAction] = useState("Extracting merchant onboarding fee schedule");

  const contextContent = (
    <>
      <div className="contextPanelHeader">
        <span>macOS CUA Security</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Safety</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div className="contextSectionTitle">System Permissions</div>
          <div className="metricKeyValue">
            <span className="metricKey">Accessibility API</span>
            <span className="metricVal" style={{ color: "#10B981" }}>Granted</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Screen Recording</span>
            <span className="metricVal" style={{ color: "#10B981" }}>Granted</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">AppleScript Sandbox</span>
            <span className="metricVal">Restricted</span>
          </div>
        </div>

        <button
          type="button"
          style={{
            padding: "8px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--status-danger-border)",
            background: "var(--status-danger-bg)",
            color: "var(--status-danger-text)",
            fontSize: "12px",
            fontWeight: 600,
          }}
          onClick={() => alert("CUA control interrupted. User has full priority.")}
        >
          Emergency Stop CUA
        </button>
      </div>
    </>
  );

  return (
    <AppShell currentRouteName="Computer Control" contextPanelContent={contextContent}>
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Computer Control (CUA)</h1>
            <p className="pageSubtitle">
              macOS desktop vision and accessibility automation under least-privilege scoping.
            </p>
          </div>

          <span className="statusBadge completed"><CheckIcon size={12} /> Connected (Mac mini)</span>
        </div>

        {/* Current State Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div className="contextSection">
            <div className="contextSectionTitle">Active Application</div>
            <strong style={{ fontSize: "15px", color: "var(--text-primary)" }}>{activeApp}</strong>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
              Focus window: 1920 × 1080 (Frontmost process)
            </div>
          </div>

          <div className="contextSection">
            <div className="contextSectionTitle">Current CUA Action</div>
            <strong style={{ fontSize: "14px", color: "var(--accent-primary)" }}>{currentAction}</strong>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
              Action triggered by Joice via Pricing Analyst
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
