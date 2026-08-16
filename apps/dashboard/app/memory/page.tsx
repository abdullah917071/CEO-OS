"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import {
  MemoryIcon,
  SearchIcon,
  CheckIcon,
} from "../../components/icons";

interface MemoryItem {
  id: string;
  category: "Profile" | "Preferences" | "Projects" | "People" | "Companies" | "Decisions" | "Knowledge";
  title: string;
  content: string;
  source: string;
  updatedAt: string;
  isPinned?: boolean;
}

const DEMO_MEMORIES: MemoryItem[] = [
  {
    id: "mem_1",
    category: "Projects",
    title: "Suppremo Operating Goals & Margin Targets",
    content: "Targeting 12% operating margin in Q3. Prioritize flat-rate merchant subscription tier over per-order commission surge.",
    source: "Executive Strategy Note",
    updatedAt: "Yesterday",
    isPinned: true,
  },
  {
    id: "mem_2",
    category: "Preferences",
    title: "Code Quality & Architecture Guardrails",
    content: "Strict Mypy type-checking, minimal diffs, no giant refactors during bug fixes, and all contracts defined prior to implementation.",
    source: "AGENTS.md",
    updatedAt: "3 days ago",
    isPinned: true,
  },
  {
    id: "mem_3",
    category: "Companies",
    title: "Swiggy & Zomato Competitor Profile",
    content: "Merchant onboarding baseline commission is 18–24% plus delivery fee surcharges. Significant user dissatisfaction with platform fees.",
    source: "Pricing Analyst Report",
    updatedAt: "Today",
    isPinned: false,
  },
  {
    id: "mem_4",
    category: "Profile",
    title: "CEO User Context & Role",
    content: "Abdullah Ansari — Primary Operator of CEO-OS. Timezone: IST (UTC+5:30). High-level autonomous delegation preferred.",
    source: "System Init",
    updatedAt: "1 week ago",
    isPinned: false,
  },
];

export default function MemoryPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [memories, setMemories] = useState<MemoryItem[]>(DEMO_MEMORIES);
  const [selectedMemory, setSelectedMemory] = useState<MemoryItem | null>(DEMO_MEMORIES[0]);

  const categories = ["All", "Profile", "Preferences", "Projects", "People", "Companies", "Decisions", "Knowledge"];

  const filteredMemories = memories.filter((m) => {
    const matchesCategory = selectedCategory === "All" || m.category === selectedCategory;
    const matchesSearch =
      m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.content.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleForget = (id: string) => {
    setMemories((prev) => prev.filter((m) => m.id !== id));
    if (selectedMemory?.id === id) setSelectedMemory(null);
  };

  const handleTogglePin = (id: string) => {
    setMemories((prev) =>
      prev.map((m) => (m.id === id ? { ...m, isPinned: !m.isPinned } : m))
    );
  };

  const contextContent = selectedMemory ? (
    <>
      <div className="contextPanelHeader">
        <span>Memory Record</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{selectedMemory.category}</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
            <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>{selectedMemory.title}</strong>
            {selectedMemory.isPinned && (
              <span style={{ fontSize: "11px", color: "var(--accent-primary)", fontWeight: 600 }}>📌 Pinned</span>
            )}
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.6", marginBottom: "12px" }}>
            {selectedMemory.content}
          </div>

          <div className="metricKeyValue">
            <span className="metricKey">Provenance</span>
            <span className="metricVal">{selectedMemory.source}</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Last Updated</span>
            <span className="metricVal">{selectedMemory.updatedAt}</span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            style={{
              flex: 1,
              padding: "7px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-strong)",
              background: "var(--bg-surface)",
              fontSize: "12px",
              fontWeight: 500,
              color: "var(--text-primary)",
            }}
            onClick={() => handleTogglePin(selectedMemory.id)}
          >
            {selectedMemory.isPinned ? "Unpin" : "Pin Memory"}
          </button>
          <button
            type="button"
            style={{
              padding: "7px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--status-danger-border)",
              background: "var(--status-danger-bg)",
              color: "var(--status-danger-text)",
              fontSize: "12px",
              fontWeight: 600,
            }}
            onClick={() => handleForget(selectedMemory.id)}
          >
            Forget
          </button>
        </div>
      </div>
    </>
  ) : null;

  return (
    <AppShell currentRouteName="Memory" contextPanelContent={contextContent}>
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Memory & State</h1>
            <p className="pageSubtitle">
              Persistent context, business rules, and preferences referenced by Joice.
            </p>
          </div>

          <div style={{ position: "relative", width: "240px" }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memory..."
              style={{
                width: "100%",
                padding: "6px 10px 6px 28px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-strong)",
                fontSize: "13px",
                outline: "none",
              }}
            />
            <span style={{ position: "absolute", left: "9px", top: "7px", color: "var(--text-muted)" }}>
              <SearchIcon size={13} />
            </span>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="filterTabBar">
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              className={`filterTab ${selectedCategory === cat ? "active" : ""}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Memory Items List */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {filteredMemories.map((mem) => (
            <div
              key={mem.id}
              onClick={() => setSelectedMemory(mem)}
              style={{
                background: selectedMemory?.id === mem.id ? "var(--bg-surface-subtle)" : "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                padding: "12px 16px",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {mem.isPinned && <span style={{ fontSize: "12px" }}>📌</span>}
                  <strong style={{ fontSize: "13px", color: "var(--text-primary)" }}>{mem.title}</strong>
                  <span
                    style={{
                      fontSize: "11px",
                      padding: "1px 6px",
                      borderRadius: "var(--radius-full)",
                      background: "var(--bg-surface-tertiary)",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {mem.category}
                  </span>
                </div>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{mem.updatedAt}</span>
              </div>

              <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                {mem.content}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
