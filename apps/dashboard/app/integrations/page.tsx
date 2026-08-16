"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { IntegrationsIcon, CheckIcon } from "../../components/icons";

interface IntegrationItem {
  id: string;
  name: string;
  category: "AI" | "Google" | "Communication" | "Developer" | "Productivity";
  status: "Connected" | "Configured" | "Disconnected";
  description: string;
}

const DEMO_INTEGRATIONS: IntegrationItem[] = [
  {
    id: "int_google_workspace",
    name: "Google Cloud Vertex AI & Gmail",
    category: "Google",
    status: "Configured",
    description: "Service Account authentication for Gemini Live and email context reading.",
  },
  {
    id: "int_github",
    name: "GitHub Repository & Actions",
    category: "Developer",
    status: "Connected",
    description: "Codebase inspection, pull request automation, and CI workflow triggering.",
  },
  {
    id: "int_openrouter",
    name: "OpenRouter & Deep Reasoning",
    category: "AI",
    status: "Connected",
    description: "Provider routing for Claude 3.5 Sonnet and high-tier reasoning engines.",
  },
  {
    id: "int_spotify",
    name: "Spotify macOS Controller",
    category: "Productivity",
    status: "Connected",
    description: "AppleScript bridge for voice playback control and focus playlists.",
  },
];

export default function IntegrationsPage() {
  const [integrations] = useState<IntegrationItem[]>(DEMO_INTEGRATIONS);

  return (
    <AppShell currentRouteName="Integrations">
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Integrations</h1>
            <p className="pageSubtitle">
              Third-party connectors, AI models, and local service providers linked to CEO-OS.
            </p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
          {integrations.map((item) => (
            <div
              key={item.id}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                padding: "16px",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>{item.name}</strong>
                <span className="statusBadge completed"><CheckIcon size={11} /> {item.status}</span>
              </div>

              <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                {item.description}
              </div>

              <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                <button
                  type="button"
                  style={{
                    padding: "4px 10px",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--bg-surface-secondary)",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "12px",
                    fontWeight: 500,
                  }}
                  onClick={() => alert(`Configured ${item.name}`)}
                >
                  Configure
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
