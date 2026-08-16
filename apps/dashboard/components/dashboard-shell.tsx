"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { API, requestJson, WS } from "../lib/api";
import type { Task } from "../lib/contracts";

const NAV_LINKS = [
  { href: "/", label: "Executive Deck", glyph: "⌁" },
  { href: "/jarvis", label: "Jarvis Voice Studio", glyph: "🎙" },
  { href: "/tasks", label: "Tasks & Engine", glyph: "✓" },
  { href: "/agents", label: "Workforce & Skills", glyph: "◉" },
  { href: "/desktop", label: "CUA Desktop Host", glyph: "🖥" },
  { href: "/integrations", label: "Capabilities & MCP", glyph: "⊞" },
  { href: "/memory", label: "Memory Vault", glyph: "◇" },
  { href: "/activity", label: "Live Telemetry", glyph: "↗" },
  { href: "/settings", label: "System Health", glyph: "⚙" },
] as const;

type LiveState = {
  connected: boolean;
  revision: number;
  activeTaskCount: number;
  totalTaskCount: number;
};

const LiveContext = createContext<LiveState>({
  connected: false,
  revision: 0,
  activeTaskCount: 0,
  totalTaskCount: 0,
});

export function useLiveState() {
  return useContext(LiveContext);
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [connected, setConnected] = useState(false);
  const [revision, setRevision] = useState(0);
  const [activeTaskCount, setActiveTaskCount] = useState(0);
  const [totalTaskCount, setTotalTaskCount] = useState(0);

  // Poll task metrics for quick indicators
  useEffect(() => {
    let unmounted = false;
    async function loadMetrics() {
      try {
        const tasks = await requestJson<Task[]>("/api/v1/tasks?limit=50");
        if (!unmounted) {
          setTotalTaskCount(tasks.length);
          const running = tasks.filter((t) =>
            ["planning", "running", "retrying", "waiting", "needs_approval"].includes(t.status)
          ).length;
          setActiveTaskCount(running);
        }
      } catch {
        // fallback gracefully if API is waking up
      }
    }
    void loadMetrics();
    const interval = setInterval(loadMetrics, 5000);
    return () => {
      unmounted = true;
      clearInterval(interval);
    };
  }, [revision]);

  // WebSocket Live Synchronization
  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let active = true;

    const connect = () => {
      try {
        socket = new WebSocket(WS);
        socket.onopen = () => {
          setConnected(true);
          setRevision((v) => v + 1);
        };
        socket.onmessage = () => {
          setRevision((v) => v + 1);
        };
        socket.onclose = () => {
          setConnected(false);
          if (active) retryTimer = setTimeout(connect, 2000);
        };
        socket.onerror = () => {
          socket?.close();
        };
      } catch {
        setConnected(false);
        if (active) retryTimer = setTimeout(connect, 3000);
      }
    };

    connect();
    return () => {
      active = false;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  const state = useMemo(
    () => ({ connected, revision, activeTaskCount, totalTaskCount }),
    [connected, revision, activeTaskCount, totalTaskCount]
  );

  return (
    <LiveContext.Provider value={state}>
      <div className="appShell">
        <aside className="sidebar">
          <Link className="brand" href="/">
            <span className="brandMark">C</span>
            <div>
              <span>CEO OS</span>
              <small>EXECUTIVE CONSOLE</small>
            </div>
          </Link>

          <nav aria-label="Primary navigation">
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              const hasBadge = link.href === "/tasks" && activeTaskCount > 0;
              return (
                <Link
                  key={link.href}
                  className={isActive ? "active" : ""}
                  href={link.href}
                >
                  <span className="navLabel">
                    <span className="navGlyph">{link.glyph}</span>
                    {link.label}
                  </span>
                  {hasBadge && (
                    <span className="navBadge">{activeTaskCount}</span>
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="sidebarFooter">
            <div className="connection">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span className={connected ? "dot live" : "dot"} />
                <span>{connected ? "LIVE EVENT SYNC" : "CONNECTING..."}</span>
              </div>
              <span style={{ opacity: 0.6 }}>v2.2</span>
            </div>
          </div>
        </aside>

        <div className="workspace">
          <header className="topbar">
            <div className="topbarInfo">
              <p className="eyebrow">AUTONOMOUS ENTERPRISE SYSTEM</p>
              <strong>Executive Command Center</strong>
            </div>

            <div className="topbarMetrics">
              <div className="metricBadge">
                <span>SECURITY</span>
                <strong>100/100</strong>
              </div>
              <div className="metricBadge">
                <span>FLEET</span>
                <strong>270+ SKILLS</strong>
              </div>
              <div className="metricBadge">
                <span>ACTIVE TASKS</span>
                <strong>{activeTaskCount}</strong>
              </div>
              <span className="mode">CEO AUTONOMOUS</span>
            </div>
          </header>

          <main>{children}</main>
        </div>
      </div>
    </LiveContext.Provider>
  );
}
