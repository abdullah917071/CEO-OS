"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLiveState } from "../../components/dashboard-shell";
import { formatDate, requestJson } from "../../lib/api";
import type { Memory } from "../../lib/contracts";

export default function MemoryPage() {
  const { revision } = useLiveState();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New memory modal
  const [showCreate, setShowCreate] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newType, setNewType] = useState("fact");
  const [newKey, setNewKey] = useState("");
  const [creating, setCreating] = useState(false);

  const loadMemories = useCallback(async () => {
    try {
      const data = await requestJson<Memory[]>("/api/v1/memory?limit=100");
      setMemories(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    }
  }, []);

  useEffect(() => {
    void loadMemories();
  }, [loadMemories, revision]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) {
      await loadMemories();
      return;
    }
    setSearching(true);
    setError(null);
    try {
      const results = await requestJson<Memory[]>("/api/v1/memory/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), limit: 50 }),
      });
      setMemories(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newContent.trim() || creating) return;
    setCreating(true);
    setError(null);
    try {
      await requestJson<Memory>("/api/v1/memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: newContent.trim(),
          memory_type: newType,
          subject_key: newKey.trim() || null,
          importance: 0.8,
        }),
      });
      setNewContent("");
      setNewKey("");
      setShowCreate(false);
      await loadMemories();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record memory");
    } finally {
      setCreating(false);
    }
  }

  const filteredMemories = useMemo(() => {
    return memories.filter((m) => {
      if (typeFilter === "all") return true;
      return m.memory_type.toLowerCase() === typeFilter.toLowerCase();
    });
  }, [memories, typeFilter]);

  return (
    <>
      <section className="pageIntro">
        <p className="eyebrow">PERSISTENT KNOWLEDGE VAULT</p>
        <h1>Long-Term Memory</h1>
        <p>
          Semantic and episodic memory store indexed with 384-dimensional vector embeddings,
          provenance tracking, and immutable correction chains.
        </p>
      </section>

      {/* Stats */}
      <div className="statGrid">
        <div className="stat highlight">
          <span>INDEXED MEMORIES</span>
          <strong>{memories.length}</strong>
          <small>Vectorized in PostgreSQL / HNSW</small>
        </div>
        <div className="stat">
          <span>FACTS & RULES</span>
          <strong>
            {memories.filter((m) => ["fact", "rule", "constraint"].includes(m.memory_type)).length}
          </strong>
        </div>
        <div className="stat">
          <span>EPISODIC HISTORY</span>
          <strong>
            {memories.filter((m) => m.memory_type === "episodic").length}
          </strong>
        </div>
        <div className="stat">
          <span>HIGH IMPORTANCE</span>
          <strong>
            {memories.filter((m) => m.importance >= 0.7).length}
          </strong>
        </div>
      </div>

      {error && <p className="notice error">Memory Error: {error}</p>}

      {/* Search & Actions */}
      <div className="searchBar">
        <form onSubmit={handleSearch} style={{ display: "flex", flex: 1, gap: "10px" }}>
          <input
            type="text"
            placeholder="Semantic search across memories (e.g. 'What are the company goals?')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" disabled={searching}>
            {searching ? "SEARCHING..." : "SEMANTIC SEARCH"}
          </button>
        </form>
        <button type="button" className="secondary" onClick={() => setShowCreate(true)}>
          + RECORD MEMORY
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="tabNav">
        <button
          type="button"
          className={`tabButton ${typeFilter === "all" ? "active" : ""}`}
          onClick={() => setTypeFilter("all")}
        >
          All Memories <span>({memories.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${typeFilter === "fact" ? "active" : ""}`}
          onClick={() => setTypeFilter("fact")}
        >
          Facts
        </button>
        <button
          type="button"
          className={`tabButton ${typeFilter === "rule" ? "active" : ""}`}
          onClick={() => setTypeFilter("rule")}
        >
          Rules
        </button>
        <button
          type="button"
          className={`tabButton ${typeFilter === "episodic" ? "active" : ""}`}
          onClick={() => setTypeFilter("episodic")}
        >
          Episodic
        </button>
        <button
          type="button"
          className={`tabButton ${typeFilter === "preference" ? "active" : ""}`}
          onClick={() => setTypeFilter("preference")}
        >
          Preferences
        </button>
      </div>

      {/* Memories Grid */}
      <div className="cards memoryGrid">
        {filteredMemories.length ? (
          filteredMemories.map((memory) => (
            <article className="card memoryCard" key={memory.id}>
              <div>
                <div className="cardHead">
                  <span className="riskBadge r0">{memory.memory_type.toUpperCase()}</span>
                  <span>{Math.round(memory.confidence * 100)}% confidence</span>
                </div>

                <p>{memory.content}</p>
              </div>

              <div>
                <div className="tagRow">
                  {memory.subject_key && <span>Key: {memory.subject_key}</span>}
                  <span>Importance: {Math.round(memory.importance * 100)}%</span>
                  {memory.score !== undefined && memory.score !== null && (
                    <span className="domainTag">
                      Similarity: {Math.round(memory.score * 100)}%
                    </span>
                  )}
                </div>

                <div className="source">
                  <span>Observed: {formatDate(memory.observed_at)}</span>
                  {memory.provenance.length > 0 && (
                    <div style={{ marginTop: "4px" }}>
                      Source: {memory.provenance.map((p) => p.source_type).join(", ")}
                    </div>
                  )}
                </div>
              </div>
            </article>
          ))
        ) : (
          <div className="emptyState" style={{ gridColumn: "1 / -1" }}>
            <strong>No memories found</strong>
            <p>Try a different search query or record a new memory.</p>
          </div>
        )}
      </div>

      {/* Create Memory Modal */}
      {showCreate && (
        <div className="modalBackdrop" onClick={() => setShowCreate(false)}>
          <div className="modalWindow" onClick={(e) => e.stopPropagation()}>
            <div className="modalHead">
              <h2>Record Knowledge Memory</h2>
              <button
                type="button"
                className="closeBtn"
                onClick={() => setShowCreate(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreate}>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "11px", color: "var(--muted)", display: "block", marginBottom: "6px" }}>
                  Memory Content
                </label>
                <textarea
                  style={{
                    width: "100%",
                    minHeight: "100px",
                    padding: "12px",
                    background: "var(--bg)",
                    border: "1px solid var(--border)",
                    color: "var(--ink)",
                    borderRadius: "var(--radius-sm)",
                  }}
                  placeholder="State the fact, rule, or preference..."
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  required
                />
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <label style={{ fontSize: "11px", color: "var(--muted)", display: "block", marginBottom: "6px" }}>
                    Memory Type
                  </label>
                  <select
                    className="filterSelect"
                    style={{ width: "100%" }}
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                  >
                    <option value="fact">Fact</option>
                    <option value="rule">Rule</option>
                    <option value="preference">Preference</option>
                    <option value="constraint">Constraint</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "var(--muted)", display: "block", marginBottom: "6px" }}>
                    Subject Key (optional)
                  </label>
                  <input
                    type="text"
                    style={{
                      width: "100%",
                      minHeight: "44px",
                      padding: "0 12px",
                      background: "var(--bg)",
                      border: "1px solid var(--border)",
                      color: "var(--ink)",
                      borderRadius: "var(--radius-sm)",
                    }}
                    placeholder="e.g. cloud_budget"
                    value={newKey}
                    onChange={(e) => setNewKey(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setShowCreate(false)}
                >
                  CANCEL
                </button>
                <button type="submit" disabled={creating || !newContent.trim()}>
                  {creating ? "SAVING..." : "COMMIT TO MEMORY"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
