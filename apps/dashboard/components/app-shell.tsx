"use client";

import React, { useState } from "react";
import { TopBar } from "./top-bar";
import { Sidebar } from "./sidebar";
import { CommandPalette } from "./command-palette";

interface AppShellProps {
  children: React.ReactNode;
  currentRouteName?: string;
  contextPanelContent?: React.ReactNode;
}

export function AppShell({
  children,
  currentRouteName = "Joice",
  contextPanelContent,
}: AppShellProps) {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(true);

  return (
    <div className="appContainer">
      {/* 1. Global Top Bar */}
      <TopBar
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onToggleContextPanel={() => setIsContextPanelOpen(!isContextPanelOpen)}
        isContextPanelOpen={isContextPanelOpen}
        currentRouteName={currentRouteName}
      />

      {/* 2. Main Body: Sidebar + Main Workspace + Context Panel */}
      <div className="appBody">
        <Sidebar />

        <main className="mainWorkspace">
          {children}
        </main>

        {contextPanelContent && (
          <aside className={`contextPanel ${!isContextPanelOpen ? "collapsed" : ""}`}>
            {contextPanelContent}
          </aside>
        )}
      </div>

      {/* 3. Global Command Palette Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectAction={(action) => {
          if (action === "start_voice") {
            window.location.href = "/jarvis";
          } else if (action === "live_view") {
            window.location.href = "/live";
          } else if (action === "tasks") {
            window.location.href = "/tasks";
          } else if (action === "memory") {
            window.location.href = "/memory";
          } else if (action === "settings") {
            window.location.href = "/settings";
          }
        }}
      />
    </div>
  );
}
