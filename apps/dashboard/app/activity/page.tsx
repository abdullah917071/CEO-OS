"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLiveState } from "../../components/dashboard-shell";
import { formatDate, requestJson, summarizePayload } from "../../lib/api";
import type { RuntimeEvent } from "../../lib/contracts";

export default function ActivityPage() {
  const { revision, connected } = useLiveState();
  const [events, setEvents] = useState<RuntimeEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("all");
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await requestJson<RuntimeEvent[]>("/api/v1/activity?limit=100");
      setEvents(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, revision]);

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (filterType === "all") return true;
      if (filterType === "task") return e.event_type.startsWith("task.");
      if (filterType === "agent") return e.event_type.startsWith("agent.");
      if (filterType === "memory") return e.event_type.startsWith("memory.");
      if (filterType === "integration") return e.event_type.startsWith("integration.");
      return true;
    });
  }, [events, filterType]);

  return (
    <>
      <section className="pageIntro">
        <p className="eyebrow">REAL-TIME TELEMETRY WATERFALL</p>
        <h1>Live Activity</h1>
        <p>
          Authoritative event hub audit stream capturing task state transitions, capability
          invocations, and agent assignments.
        </p>
      </section>

      {/* Stats */}
      <div className="statGrid">
        <div className="stat highlight">
          <span>EVENT STREAM</span>
          <strong>{events.length}</strong>
          <small>{connected ? "Streaming over WebSocket" : "Reconnecting"}</small>
        </div>
        <div className="stat">
          <span>TASK EVENTS</span>
          <strong>{events.filter((e) => e.event_type.startsWith("task.")).length}</strong>
        </div>
        <div className="stat">
          <span>AGENT EVENTS</span>
          <strong>{events.filter((e) => e.event_type.startsWith("agent.")).length}</strong>
        </div>
        <div className="stat">
          <span>INTEGRATION EVENTS</span>
          <strong>{events.filter((e) => e.event_type.startsWith("integration.")).length}</strong>
        </div>
      </div>

      {error && <p className="notice error">CEO API: {error}</p>}

      {/* Filter Tabs */}
      <div className="tabNav">
        <button
          type="button"
          className={`tabButton ${filterType === "all" ? "active" : ""}`}
          onClick={() => setFilterType("all")}
        >
          All Events <span>({events.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${filterType === "task" ? "active" : ""}`}
          onClick={() => setFilterType("task")}
        >
          Task Lifecycle
        </button>
        <button
          type="button"
          className={`tabButton ${filterType === "agent" ? "active" : ""}`}
          onClick={() => setFilterType("agent")}
        >
          Agent Fleet
        </button>
        <button
          type="button"
          className={`tabButton ${filterType === "memory" ? "active" : ""}`}
          onClick={() => setFilterType("memory")}
        >
          Memory Operations
        </button>
      </div>

      {/* Timeline Stream */}
      <div className="timeline">
        {filteredEvents.length ? (
          filteredEvents.map((item, index) => {
            const isExpanded = expandedIndex === index;
            return (
              <div className="event" key={`${item.occurred_at}-${index}`}>
                <span className="eventDot" />
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span className="riskBadge r0">{item.event_type}</span>
                    {item.task_id && (
                      <span style={{ fontSize: "10px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                        Task: {item.task_id.slice(0, 8)}...
                      </span>
                    )}
                  </div>
                  <small>{formatDate(item.occurred_at)}</small>
                </div>

                <p style={{ marginTop: "6px", color: "var(--ink-subtle)", fontSize: "13px" }}>
                  {summarizePayload(item.payload)}
                </p>

                <div style={{ marginTop: "8px" }}>
                  <button
                    type="button"
                    className="secondary"
                    style={{ minHeight: "26px", padding: "0 8px", fontSize: "9px" }}
                    onClick={() => setExpandedIndex(isExpanded ? null : index)}
                  >
                    {isExpanded ? "HIDE PAYLOAD" : "VIEW PAYLOAD JSON"}
                  </button>
                </div>

                {isExpanded && (
                  <pre
                    style={{
                      marginTop: "8px",
                      padding: "10px",
                      background: "var(--bg)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "11px",
                      fontFamily: "var(--font-mono)",
                      overflowX: "auto",
                    }}
                  >
                    {JSON.stringify(item.payload, null, 2)}
                  </pre>
                )}
              </div>
            );
          })
        ) : (
          <div className="emptyState">
            <strong>No activity events recorded</strong>
            <p>Events will stream live as tasks and agents execute.</p>
          </div>
        )}
      </div>
    </>
  );
}
