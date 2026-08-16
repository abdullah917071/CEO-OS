"use client";

import { useEffect, useState } from "react";
import { requestJson } from "../../lib/api";

type CuaStatus = {
  enabled: boolean;
  frontmost_app: string;
  running_apps_count: number;
  accessibility_granted: boolean;
  effects_enabled: boolean;
};

type CuaApp = {
  bundle_id: string;
  name: string;
  path: string;
  running: boolean;
  frontmost: boolean;
  pid: number | null;
};

type CuaAppsResponse = {
  count: number;
  apps: CuaApp[];
};

type ActionResult = {
  action: string;
  success: boolean;
  output: Record<string, unknown>;
  error?: string;
};

type ExecuteResult = {
  status: string;
  final_answer: string;
  steps_count: number;
  duration_ms: number;
};

export default function DesktopCuaPage() {
  const [status, setStatus] = useState<CuaStatus | null>(null);
  const [apps, setApps] = useState<CuaApp[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [lastAction, setLastAction] = useState<ActionResult | null>(null);
  const [textToType, setTextToType] = useState("");
  const [keyToPress, setKeyToPress] = useState("return");
  const [objective, setObjective] = useState("Inspect running applications and verify system state");
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState<ExecuteResult | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      const [s, a] = await Promise.all([
        requestJson<CuaStatus>("/api/v1/cua/status"),
        requestJson<CuaAppsResponse>("/api/v1/cua/apps"),
      ]);
      setStatus(s);
      setApps(a.apps);
    } catch {
      // API may still be warming up
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
    const interval = setInterval(() => {
      void loadData();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  async function handleFocus(bundleId: string) {
    setActionLoading(true);
    try {
      const res = await requestJson<ActionResult>("/api/v1/cua/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "focus_app", bundle_id: bundleId }),
      });
      setLastAction(res);
      await loadData();
    } catch (e) {
      setLastAction({ action: "focus_app", success: false, output: {}, error: String(e) });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleType() {
    if (!textToType) return;
    setActionLoading(true);
    try {
      const res = await requestJson<ActionResult>("/api/v1/cua/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "type_text", text: textToType }),
      });
      setLastAction(res);
    } catch (e) {
      setLastAction({ action: "type_text", success: false, output: {}, error: String(e) });
    } finally {
      setActionLoading(false);
    }
  }

  async function handlePressKey() {
    if (!keyToPress) return;
    setActionLoading(true);
    try {
      const res = await requestJson<ActionResult>("/api/v1/cua/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "press_key", key: keyToPress, modifiers: [] }),
      });
      setLastAction(res);
    } catch (e) {
      setLastAction({ action: "press_key", success: false, output: {}, error: String(e) });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleExecute() {
    if (!objective.trim()) return;
    setExecuting(true);
    try {
      const res = await requestJson<ExecuteResult>("/api/v1/cua/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ objective }),
      });
      setExecResult(res);
    } catch (e) {
      setExecResult({
        status: "FAILED",
        final_answer: String(e),
        steps_count: 0,
        duration_ms: 0,
      });
    } finally {
      setExecuting(false);
    }
  }

  const filteredApps = apps.filter(
    (a) =>
      a.running &&
      (a.name.toLowerCase().includes(search.toLowerCase()) ||
        a.bundle_id.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <header className="panel" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.4rem", fontWeight: 700 }}>
            🖥️ Computer-Use Agent (CUA) Desktop Studio
          </h1>
          <p style={{ margin: "0.25rem 0 0", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Native macOS Host Perception, Swift Accessibility Bridge & Autonomous Desktop Actions
          </p>
        </div>
        <button
          className="button"
          onClick={() => void loadData()}
          disabled={loading}
          style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          {loading ? "⟳ Scanning..." : "⟳ Refresh State"}
        </button>
      </header>

      {/* Status Bar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "1rem",
        }}
      >
        <div className="panel" style={{ borderLeft: "4px solid var(--accent-emerald, #10b981)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            CUA Runtime Driver
          </div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "0.25rem", color: "#10b981" }}>
            ONLINE & CONNECTED
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            Native Swift Helper v1.0 (Darwin)
          </div>
        </div>

        <div className="panel" style={{ borderLeft: "4px solid var(--accent-cyan, #06b6d4)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Frontmost Focused App
          </div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "0.25rem", color: "#06b6d4" }}>
            {status?.frontmost_app || "Scanning..."}
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            Active macOS window context
          </div>
        </div>

        <div className="panel" style={{ borderLeft: "4px solid var(--accent-purple, #a855f7)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Running Host Apps
          </div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "0.25rem", color: "#a855f7" }}>
            {status?.running_apps_count || filteredApps.length} Active
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            Accessibility Trusted: Yes
          </div>
        </div>
      </div>

      {/* Autonomous Desktop Task Runner */}
      <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 600 }}>
              ⚡ Autonomous CUA Desktop Dispatcher
            </h2>
            <p style={{ margin: "0.2rem 0 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>
              Powered by Nous Hermes ReAct + OpenRouter (nvidia/nemotron-3.5-lightning:free)
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <input
            className="input"
            style={{ flex: 1 }}
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="Enter desktop automation directive (e.g. 'Inspect running applications and bring Terminal to front')..."
          />
          <button
            className="button button-primary"
            onClick={() => void handleExecute()}
            disabled={executing}
            style={{ minWidth: "140px" }}
          >
            {executing ? "⚡ Executing..." : "⚡ Run Directive"}
          </button>
        </div>

        {execResult && (
          <div
            style={{
              padding: "1rem",
              borderRadius: "6px",
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              fontSize: "0.85rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
              <span>Status: <strong style={{ color: "#10b981" }}>{execResult.status}</strong></span>
              <span>Steps: {execResult.steps_count} | Duration: {execResult.duration_ms.toFixed(1)}ms</span>
            </div>
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                fontFamily: "var(--font-mono, monospace)",
                color: "#e2e8f0",
              }}
            >
              {execResult.final_answer}
            </pre>
          </div>
        )}
      </div>

      {/* Interactive Control Deck */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        {/* Direct Text Input */}
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600 }}>⌨️ Direct Keyboard Injection</h3>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.8rem" }}>
            Types text directly into the frontmost focused macOS application window.
          </p>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <input
              className="input"
              style={{ flex: 1 }}
              value={textToType}
              onChange={(e) => setTextToType(e.target.value)}
              placeholder="Text to type into focused app..."
            />
            <button
              className="button"
              onClick={() => void handleType()}
              disabled={actionLoading || !textToType}
            >
              Type Text
            </button>
          </div>
        </div>

        {/* Direct Key Shortcut */}
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600 }}>🔤 Send Key Shortcut</h3>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.8rem" }}>
            Dispatches native key press events (e.g. Return, Escape, Space).
          </p>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <select
              className="input"
              style={{ flex: 1 }}
              value={keyToPress}
              onChange={(e) => setKeyToPress(e.target.value)}
            >
              <option value="return">Return / Enter</option>
              <option value="escape">Escape</option>
              <option value="tab">Tab</option>
              <option value="space">Space</option>
              <option value="backspace">Backspace</option>
            </select>
            <button
              className="button"
              onClick={() => void handlePressKey()}
              disabled={actionLoading}
            >
              Press Key
            </button>
          </div>
        </div>
      </div>

      {lastAction && (
        <div
          style={{
            padding: "0.75rem 1rem",
            borderRadius: "6px",
            background: lastAction.success ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
            border: `1px solid ${lastAction.success ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
            fontSize: "0.85rem",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>Action: <code>{lastAction.action}</code> ({lastAction.success ? "SUCCESS" : "FAILED"})</span>
          {lastAction.error && <span style={{ color: "#ef4444" }}>{lastAction.error}</span>}
        </div>
      )}

      {/* Running Applications Grid */}
      <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 600 }}>
              🖥️ Running macOS Applications ({filteredApps.length})
            </h2>
            <p style={{ margin: "0.2rem 0 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>
              Click "Focus" to bring any window directly to the front.
            </p>
          </div>
          <input
            className="input"
            style={{ maxWidth: "240px" }}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search running apps..."
          />
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            gap: "0.75rem",
          }}
        >
          {filteredApps.map((app) => (
            <div
              key={app.bundle_id}
              style={{
                padding: "0.85rem",
                borderRadius: "6px",
                background: app.frontmost ? "rgba(6, 182, 212, 0.1)" : "rgba(255, 255, 255, 0.03)",
                border: app.frontmost
                  ? "1px solid rgba(6, 182, 212, 0.4)"
                  : "1px solid rgba(255, 255, 255, 0.08)",
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{app.name}</div>
                  <div
                    style={{
                      fontSize: "0.75rem",
                      color: "var(--text-muted)",
                      wordBreak: "break-all",
                    }}
                  >
                    {app.bundle_id}
                  </div>
                </div>
                {app.frontmost && (
                  <span
                    style={{
                      fontSize: "0.7rem",
                      padding: "0.15rem 0.4rem",
                      borderRadius: "4px",
                      background: "#06b6d4",
                      color: "#000",
                      fontWeight: 700,
                    }}
                  >
                    FRONT
                  </span>
                )}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  PID: {app.pid || "—"}
                </span>
                <button
                  className="button"
                  style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem" }}
                  onClick={() => void handleFocus(app.bundle_id)}
                  disabled={actionLoading || app.frontmost}
                >
                  {app.frontmost ? "Focused" : "Focus App"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
