"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { SkillsIcon, CheckIcon } from "../../components/icons";

interface SkillItem {
  id: string;
  name: string;
  provider: string;
  description: string;
  agentsCount: number;
  enabled: boolean;
}

const DEMO_SKILLS: SkillItem[] = [
  {
    id: "skill_browser_navigate",
    name: "Web Navigation & DOM Extraction",
    provider: "Browser Subsystem",
    description: "Launches Playwright sessions, reads page markup, and extracts structured content.",
    agentsCount: 14,
    enabled: true,
  },
  {
    id: "skill_applescript_control",
    name: "macOS System & App Automation",
    provider: "Jarvis CUA Subsystem",
    description: "Executes AppleScript directives, focuses active windows, and controls media playback.",
    agentsCount: 8,
    enabled: true,
  },
  {
    id: "skill_memory_semantic",
    name: "Semantic Vector Search & Retrieval",
    provider: "Memory Engine",
    description: "Queries workspace embeddings and sqlite-vec memory indexes for contextual knowledge.",
    agentsCount: 22,
    enabled: true,
  },
  {
    id: "skill_code_analysis",
    name: "Repository AST & Diff Analysis",
    provider: "gstack Engine",
    description: "Performs AST-level syntax checks, imports verification, and quality gate evaluations.",
    agentsCount: 11,
    enabled: true,
  },
];

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillItem[]>(DEMO_SKILLS);

  const toggleSkill = (id: string) => {
    setSkills((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s))
    );
  };

  return (
    <AppShell currentRouteName="Skills">
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Skills Catalog</h1>
            <p className="pageSubtitle">
              Modular capabilities, tool bindings, and domain procedures available to agents.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {skills.map((skill) => (
            <div
              key={skill.id}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                padding: "14px 18px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>{skill.name}</strong>
                  <span
                    style={{
                      fontSize: "11px",
                      padding: "1px 6px",
                      borderRadius: "var(--radius-full)",
                      background: "var(--bg-surface-secondary)",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {skill.provider}
                  </span>
                </div>
                <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "3px" }}>
                  {skill.description}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  {skill.agentsCount} agents bound
                </span>
                <button
                  type="button"
                  onClick={() => toggleSkill(skill.id)}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "12px",
                    fontWeight: 600,
                    background: skill.enabled ? "var(--status-success-bg)" : "var(--bg-surface-secondary)",
                    color: skill.enabled ? "var(--status-success-text)" : "var(--text-muted)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  {skill.enabled ? "Enabled" : "Disabled"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
