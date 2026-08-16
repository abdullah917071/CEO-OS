"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { SettingsIcon, CheckIcon } from "../../components/icons";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<
    | "General"
    | "Joice"
    | "Jarvis"
    | "AI Models"
    | "Voice"
    | "Computer"
    | "Appearance"
    | "Security"
    | "Advanced"
  >("General");

  const [wakeWord, setWakeWord] = useState("Jarvis");
  const [primaryModel, setPrimaryModel] = useState("claude-3.5-sonnet");
  const [themeMode, setThemeMode] = useState("Light");

  const tabs = [
    "General",
    "Joice",
    "Jarvis",
    "AI Models",
    "Voice",
    "Computer",
    "Appearance",
    "Security",
    "Advanced",
  ] as const;

  return (
    <AppShell currentRouteName="Settings">
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Settings</h1>
            <p className="pageSubtitle">
              System preferences, model routing, voice parameters, and security policies.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: "24px" }}>
          {/* Settings Navigation */}
          <div style={{ width: "180px", display: "flex", flexDirection: "column", gap: "2px" }}>
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                style={{
                  textAlign: "left",
                  padding: "7px 12px",
                  borderRadius: "var(--radius-md)",
                  fontSize: "13px",
                  fontWeight: activeTab === tab ? 600 : 500,
                  background: activeTab === tab ? "var(--bg-surface-subtle)" : "transparent",
                  color: activeTab === tab ? "var(--text-primary)" : "var(--text-secondary)",
                  border: activeTab === tab ? "1px solid var(--border-subtle)" : "1px solid transparent",
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Settings Pane */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "16px" }}>
            {activeTab === "General" && (
              <div className="contextSection">
                <div className="contextSectionTitle">General Preferences</div>
                <div className="metricKeyValue">
                  <span className="metricKey">Operator Name</span>
                  <span className="metricVal">Abdullah Ansari</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Timezone</span>
                  <span className="metricVal">Asia/Kolkata (IST · UTC+5:30)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Default Workspace</span>
                  <span className="metricVal">CEO-OS Local</span>
                </div>
              </div>
            )}

            {activeTab === "Joice" && (
              <div className="contextSection">
                <div className="contextSectionTitle">Joice Intelligence Engine</div>
                <div className="metricKeyValue">
                  <span className="metricKey">Primary Reasoning Tier</span>
                  <span className="metricVal">High (Autonomous Swarm)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Default ReAct Reflection</span>
                  <span className="metricVal">Enabled (Auto-validate diffs)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Proactive Suggestions</span>
                  <span className="metricVal">Enabled</span>
                </div>
              </div>
            )}

            {activeTab === "Jarvis" && (
              <div className="contextSection">
                <div className="contextSectionTitle">Jarvis Ambient Assistant</div>
                <div className="metricKeyValue">
                  <span className="metricKey">Wake Word</span>
                  <span className="metricVal">Jarvis (Local openWakeWord)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Inactivity Timeout</span>
                  <span className="metricVal">60 seconds</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Realtime API Cost</span>
                  <span className="metricVal">$0.00 while idle</span>
                </div>
              </div>
            )}

            {activeTab === "AI Models" && (
              <div className="contextSection">
                <div className="contextSectionTitle">Model Provider Routing</div>
                <div className="metricKeyValue">
                  <span className="metricKey">Joice Reasoning</span>
                  <span className="metricVal">Anthropic Claude 3.5 Sonnet</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Jarvis Realtime Live</span>
                  <span className="metricVal">Google Gemini Multimodal Live</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Fast Classification</span>
                  <span className="metricVal">Gemini 3.7 Flash</span>
                </div>
              </div>
            )}

            {activeTab === "Appearance" && (
              <div className="contextSection">
                <div className="contextSectionTitle">Appearance & Theme</div>
                <div className="metricKeyValue">
                  <span className="metricKey">Default Theme</span>
                  <span className="metricVal">Light (Linear / Notion Clean)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Interface Font</span>
                  <span className="metricVal">Inter (Compact scale)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Monospace Font</span>
                  <span className="metricVal">SFMono-Regular / ui-monospace</span>
                </div>
              </div>
            )}

            {activeTab === "Security" && (
              <div className="contextSection">
                <div className="contextSectionTitle">Security & Capabilities</div>
                <div className="metricKeyValue">
                  <span className="metricKey">Workspace Scoping</span>
                  <span className="metricVal" style={{ color: "#10B981" }}>Least Privilege (Enforced)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Secret Redaction</span>
                  <span className="metricVal" style={{ color: "#10B981" }}>Active in all logs</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Service Account Keys</span>
                  <span className="metricVal">0600 Filesystem Permissions</span>
                </div>
              </div>
            )}

            {activeTab === "Advanced" && (
              <div className="contextSection">
                <div className="contextSectionTitle">System Diagnostics</div>
                <div className="metricKeyValue">
                  <span className="metricKey">API Server</span>
                  <span className="metricVal">FastAPI Uvicorn (Port 8000)</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">Dashboard Runtime</span>
                  <span className="metricVal">Next.js 16.3.1 · React 19</span>
                </div>
                <div className="metricKeyValue">
                  <span className="metricKey">SQLite Database</span>
                  <span className="metricVal">data/ceo_os.db (WAL Mode)</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
