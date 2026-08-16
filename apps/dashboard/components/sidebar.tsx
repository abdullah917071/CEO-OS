"use client";

import React, { memo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  JoiceIcon,
  LiveIcon,
  TasksIcon,
  AgentsIcon,
  AutomationsIcon,
  MemoryIcon,
  BrowserIcon,
  ComputerIcon,
  CommunicationsIcon,
  IntegrationsIcon,
  SkillsIcon,
  ActivityIcon,
  SettingsIcon,
  JarvisIcon,
} from "./icons";

interface SidebarProps {
  activeRunningCount?: number;
}

export const Sidebar = memo(function Sidebar({ activeRunningCount = 3 }: SidebarProps) {
  const pathname = usePathname();

  const isNavActive = (href: string) => {
    if (href === "/" && pathname === "/") return true;
    if (href !== "/" && pathname.startsWith(href)) return true;
    return false;
  };

  return (
    <aside className="sidebar">
      <div className="sidebarTop">
        {/* Brand */}
        <div className="sidebarBrand">
          <span className="sidebarBrandDot" />
          <span>CEO-OS</span>
        </div>

        {/* Primary Intelligence & Operations */}
        <div className="navSection">
          <div className="navSectionTitle">Core Intelligence</div>
          <Link href="/" className={`navItem ${isNavActive("/") ? "active" : ""}`}>
            <JoiceIcon size={16} />
            <span>Joice</span>
          </Link>
          <Link href="/jarvis" className={`navItem ${isNavActive("/jarvis") ? "active" : ""}`}>
            <JarvisIcon size={16} />
            <span>Jarvis Voice</span>
          </Link>
          <Link href="/live" className={`navItem ${isNavActive("/live") ? "active" : ""}`}>
            <LiveIcon size={16} />
            <span>Live</span>
            {activeRunningCount > 0 && (
              <span className="navItemBadge activePulse">{activeRunningCount}</span>
            )}
          </Link>
          <Link href="/tasks" className={`navItem ${isNavActive("/tasks") ? "active" : ""}`}>
            <TasksIcon size={16} />
            <span>Tasks</span>
          </Link>
          <Link href="/agents" className={`navItem ${isNavActive("/agents") ? "active" : ""}`}>
            <AgentsIcon size={16} />
            <span>Agents</span>
          </Link>
          <Link href="/automations" className={`navItem ${isNavActive("/automations") ? "active" : ""}`}>
            <AutomationsIcon size={16} />
            <span>Automations</span>
          </Link>
          <Link href="/memory" className={`navItem ${isNavActive("/memory") ? "active" : ""}`}>
            <MemoryIcon size={16} />
            <span>Memory</span>
          </Link>
        </div>

        {/* Tools & Devices */}
        <div className="navSection">
          <div className="navSectionTitle">Tools & Control</div>
          <Link href="/browser" className={`navItem ${isNavActive("/browser") ? "active" : ""}`}>
            <BrowserIcon size={16} />
            <span>Browser</span>
          </Link>
          <Link href="/desktop" className={`navItem ${isNavActive("/desktop") ? "active" : ""}`}>
            <ComputerIcon size={16} />
            <span>Computer</span>
          </Link>
          <Link href="/communications" className={`navItem ${isNavActive("/communications") ? "active" : ""}`}>
            <CommunicationsIcon size={16} />
            <span>Communications</span>
          </Link>
          <Link href="/integrations" className={`navItem ${isNavActive("/integrations") ? "active" : ""}`}>
            <IntegrationsIcon size={16} />
            <span>Integrations</span>
          </Link>
          <Link href="/skills" className={`navItem ${isNavActive("/skills") ? "active" : ""}`}>
            <SkillsIcon size={16} />
            <span>Skills</span>
          </Link>
        </div>

        {/* System & Audit */}
        <div className="navSection">
          <div className="navSectionTitle">System</div>
          <Link href="/activity" className={`navItem ${isNavActive("/activity") ? "active" : ""}`}>
            <ActivityIcon size={16} />
            <span>Activity</span>
          </Link>
          <Link href="/settings" className={`navItem ${isNavActive("/settings") ? "active" : ""}`}>
            <SettingsIcon size={16} />
            <span>Settings</span>
          </Link>
        </div>
      </div>

      {/* Sidebar Bottom: Status Indicators */}
      <div className="sidebarBottom">
        <div className="systemStatusPill">
          <span>Jarvis</span>
          <div className="statusIndicatorGroup">
            <span className="statusMiniDot" />
            <span style={{ fontSize: "11px", fontWeight: 600 }}>Ready</span>
          </div>
        </div>
        <div className="systemStatusPill" style={{ marginBottom: 0 }}>
          <span>CEO Kernel</span>
          <div className="statusIndicatorGroup">
            <span className="statusMiniDot" />
            <span style={{ fontSize: "11px", fontWeight: 600 }}>Online</span>
          </div>
        </div>
      </div>
    </aside>
  );
});
