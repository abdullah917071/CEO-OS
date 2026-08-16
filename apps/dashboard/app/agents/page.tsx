"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { AgentsIcon, CheckIcon } from "../../components/icons";

interface AgentRecord {
  id: string;
  name: string;
  role: string;
  domain: string;
  source: string;
  capabilities: string[];
  tools: string[];
  status: "ready" | "busy";
  description: string;
}

const DEMO_AGENTS: AgentRecord[] = [
  {
    id: "agency_frontend_developer",
    name: "Frontend Engineer",
    role: "UI Architecture & React Specialist",
    domain: "Engineering",
    source: "Agency Agents",
    capabilities: ["React 19 / Next.js", "Design Tokens", "CSS Layouts", "TypeScript"],
    tools: ["read_file", "write_to_file", "build_runner", "search_code"],
    status: "busy",
    description: "Expert frontend developer specializing in modern web architecture, clean component design, and UI performance.",
  },
  {
    id: "agency_pricing_analyst",
    name: "Pricing Analyst",
    role: "Financial & Margins Specialist",
    domain: "Strategy & Finance",
    source: "Agency Agents",
    capabilities: ["Unit Economics", "Competitive Pricing", "Margin Optimization"],
    tools: ["browser.navigate", "search.google", "analytics.query"],
    status: "busy",
    description: "Develops optimal pricing models through market research, competitor analysis, cost structure evaluation, and margin modeling.",
  },
  {
    id: "agency_security_auditor",
    name: "Application Security Engineer",
    role: "AppSec Specialist",
    domain: "Engineering",
    source: "Agency Agents",
    capabilities: ["Threat Modeling", "Secure Code Review", "Secret Leak Detection"],
    tools: ["security.scan", "read_file", "policy.verify"],
    status: "ready",
    description: "Secures software development lifecycle through threat modeling, least-privilege verification, and secure code review.",
  },
  {
    id: "agency_ux_researcher",
    name: "Sentiment & UX Researcher",
    role: "User Experience Analyst",
    domain: "Research",
    source: "Agency Agents",
    capabilities: ["User Feedback Synthesis", "Review Analysis", "UX Auditing"],
    tools: ["browser.inspect", "memory.search"],
    status: "ready",
    description: "Extracts actionable insights from customer feedback, Play Store reviews, and competitive UX journeys.",
  },
  {
    id: "gstack_code_reviewer",
    name: "gstack Code Reviewer",
    role: "Automated QA & Code Gate",
    domain: "Engineering",
    source: "gstack",
    capabilities: ["Multi-file Diffs", "Regression Prevention", "Architecture Guardrails"],
    tools: ["git.diff", "read_file", "linter.run"],
    status: "ready",
    description: "Deterministic quality gate enforcing repository rules, architecture boundaries, and minimal-diff discipline.",
  },
];

export default function AgentsPage() {
  const [selectedDomain, setSelectedDomain] = useState<string>("All");
  const [selectedAgent, setSelectedAgent] = useState<AgentRecord | null>(DEMO_AGENTS[0]);

  const filteredAgents = DEMO_AGENTS.filter((a) => {
    if (selectedDomain === "All") return true;
    return a.domain === selectedDomain;
  });

  const contextContent = selectedAgent ? (
    <>
      <div className="contextPanelHeader">
        <span>Agent Profile</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{selectedAgent.source}</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-primary)", marginBottom: "2px" }}>
            {selectedAgent.name}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px" }}>
            {selectedAgent.role}
          </div>
          <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
            <span className={`statusBadge ${selectedAgent.status === "ready" ? "completed" : "running"}`}>
              {selectedAgent.status === "ready" ? "Ready" : "Active on Task"}
            </span>
          </div>

          <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
            {selectedAgent.description}
          </div>
        </div>

        {/* Capabilities */}
        <div className="contextSection">
          <div className="contextSectionTitle">Capabilities</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
            {selectedAgent.capabilities.map((cap) => (
              <span
                key={cap}
                style={{
                  fontSize: "12px",
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-surface-secondary)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {cap}
              </span>
            ))}
          </div>
        </div>

        {/* Bound Tools */}
        <div className="contextSection">
          <div className="contextSectionTitle">Allowed Tools (Least Privilege)</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
            {selectedAgent.tools.map((tool) => (
              <span
                key={tool}
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: "var(--bg-surface-tertiary)",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      </div>
    </>
  ) : null;

  return (
    <AppShell currentRouteName="Agents" contextPanelContent={contextContent}>
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Agents Directory</h1>
            <p className="pageSubtitle">
              Specialized intelligence and multi-agent fleet available to Joice.
            </p>
          </div>

          <div className="filterTabBar">
            {["All", "Engineering", "Strategy & Finance", "Research"].map((domain) => (
              <button
                key={domain}
                type="button"
                className={`filterTab ${selectedDomain === domain ? "active" : ""}`}
                onClick={() => setSelectedDomain(domain)}
              >
                {domain}
              </button>
            ))}
          </div>
        </div>

        <table className="cleanTable">
          <thead>
            <tr>
              <th>Agent</th>
              <th>Domain</th>
              <th>Source</th>
              <th>Status</th>
              <th>Bound Tools</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredAgents.map((a) => (
              <tr
                key={a.id}
                onClick={() => setSelectedAgent(a)}
                style={{
                  cursor: "pointer",
                  background: selectedAgent?.id === a.id ? "var(--bg-surface-subtle)" : undefined,
                }}
              >
                <td>
                  <strong style={{ fontSize: "13px", color: "var(--text-primary)" }}>{a.name}</strong>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{a.role}</div>
                </td>
                <td style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{a.domain}</td>
                <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>{a.source}</td>
                <td>
                  <span className={`statusBadge ${a.status === "ready" ? "completed" : "running"}`}>
                    {a.status === "ready" ? "Ready" : "Active"}
                  </span>
                </td>
                <td>
                  <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                    {a.tools.slice(0, 2).map((t) => (
                      <span
                        key={t}
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          padding: "1px 5px",
                          background: "var(--bg-surface-secondary)",
                          borderRadius: "3px",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {t}
                      </span>
                    ))}
                    {a.tools.length > 2 && (
                      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                        +{a.tools.length - 2}
                      </span>
                    )}
                  </div>
                </td>
                <td>
                  <span style={{ fontSize: "12px", color: "var(--accent-primary)", fontWeight: 500 }}>
                    Profile →
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
