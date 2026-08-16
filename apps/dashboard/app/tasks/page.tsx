"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLiveState } from "../../components/dashboard-shell";
import { TaskCard } from "../../components/task-card";
import { requestJson } from "../../lib/api";
import type { Task } from "../../lib/contracts";

type FilterStatus = "all" | "active" | "success" | "failed" | "cancelled" | "waiting";

export default function TasksPage() {
  const { revision } = useLiveState();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("all");
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setRefreshing(true);
      const data = await requestJson<Task[]>("/api/v1/tasks?limit=100");
      setTasks(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, revision]);

  const filteredTasks = useMemo(() => {
    return tasks.filter((t) => {
      const matchesSearch =
        searchQuery === "" ||
        t.objective.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.result?.message && t.result.message.toLowerCase().includes(searchQuery.toLowerCase()));

      if (!matchesSearch) return false;

      if (statusFilter === "all") return true;
      if (statusFilter === "active") {
        return ["planning", "running", "retrying"].includes(t.status);
      }
      if (statusFilter === "success") {
        return ["success", "partial_success"].includes(t.status);
      }
      if (statusFilter === "failed") {
        return t.status === "failed";
      }
      if (statusFilter === "cancelled") {
        return t.status === "cancelled";
      }
      if (statusFilter === "waiting") {
        return ["waiting", "needs_approval", "paused"].includes(t.status);
      }
      return true;
    });
  }, [tasks, searchQuery, statusFilter]);

  const activeCount = tasks.filter((t) =>
    ["planning", "running", "retrying"].includes(t.status)
  ).length;
  const successCount = tasks.filter((t) =>
    ["success", "partial_success"].includes(t.status)
  ).length;
  const failedCount = tasks.filter((t) => t.status === "failed").length;

  return (
    <>
      <section className="pageIntro">
        <p className="eyebrow">DURABLE ENGINE & ORCHESTRATION</p>
        <h1>Tasks Workbench</h1>
        <p>
          Inspect checkpointed execution plans, step transitions, risk classifications, and verified
          evidence logs.
        </p>
      </section>

      {/* Task Telemetry Metrics */}
      <div className="statGrid">
        <div className="stat">
          <span>TOTAL LOGGED</span>
          <strong>{tasks.length}</strong>
        </div>
        <div className="stat highlight">
          <span>RUNNING / ACTIVE</span>
          <strong>{activeCount}</strong>
        </div>
        <div className="stat">
          <span>SUCCESSFUL</span>
          <strong>{successCount}</strong>
        </div>
        <div className="stat">
          <span>FAILED / CANCELLED</span>
          <strong>{failedCount}</strong>
        </div>
      </div>

      {error && <p className="notice error">CEO API Error: {error}</p>}

      {/* Filter and Search Bar */}
      <div className="searchBar">
        <input
          type="text"
          placeholder="Filter tasks by objective, capability, or ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button
          type="button"
          className="secondary"
          disabled={refreshing}
          onClick={() => void refresh()}
        >
          {refreshing ? "REFRESHING..." : "REFRESH"}
        </button>
      </div>

      {/* Segmented Filter Tabs */}
      <div className="tabNav">
        <button
          type="button"
          className={`tabButton ${statusFilter === "all" ? "active" : ""}`}
          onClick={() => setStatusFilter("all")}
        >
          All Tasks <span>({tasks.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${statusFilter === "active" ? "active" : ""}`}
          onClick={() => setStatusFilter("active")}
        >
          Active / Running <span>({activeCount})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${statusFilter === "success" ? "active" : ""}`}
          onClick={() => setStatusFilter("success")}
        >
          Success <span>({successCount})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${statusFilter === "failed" ? "active" : ""}`}
          onClick={() => setStatusFilter("failed")}
        >
          Failed <span>({failedCount})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${statusFilter === "cancelled" ? "active" : ""}`}
          onClick={() => setStatusFilter("cancelled")}
        >
          Cancelled
        </button>
      </div>

      {/* Tasks List */}
      <div className="cards">
        {filteredTasks.length ? (
          filteredTasks.map((task) => (
            <TaskCard key={task.id} task={task} onChanged={() => void refresh()} />
          ))
        ) : (
          <div className="emptyState">
            <strong>No tasks match filter criteria</strong>
            <p>Try clearing your search query or changing the status filter.</p>
          </div>
        )}
      </div>
    </>
  );
}
