"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Activity,
  AlertTriangle,
  Bot,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
  Wifi,
  Settings,
  HelpCircle,
  ClipboardCheck,
  Ruler,
  ScrollText,
  Workflow,
  Plug,
} from "lucide-react";
import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { AgentCore } from "@/components/agent/AgentCore";
import SettingsModal from "./SettingsModal";

type NavItem = {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string; strokeWidth?: number }>;
  badgeFromStore?: boolean;
  ai?: boolean;
};

// Grouped so day-to-day work sits up top and the "set up once" pages read as
// secondary — a non-technical engineer isn't faced with a flat wall of 10 links.
const navSections: { section: string; items: NavItem[] }[] = [
  {
    section: "Monitor",
    items: [
      { id: "dashboard", label: "Overview", icon: LayoutDashboard },
      { id: "spc", label: "SPC Monitor", icon: Activity },
      { id: "alerts", label: "Alert Inbox", icon: AlertTriangle, badgeFromStore: true },
      { id: "review", label: "Review Queue", icon: ClipboardCheck },
    ],
  },
  {
    section: "Quality Tools",
    items: [
      { id: "grr", label: "GR&R Studies", icon: FlaskConical },
      { id: "gages", label: "Gage Registry", icon: Ruler },
      { id: "agent", label: "AI Agent", icon: Bot, ai: true },
    ],
  },
  {
    section: "Setup",
    items: [
      { id: "alert-rules", label: "Alert Rules", icon: Workflow },
      { id: "integrations", label: "Connections", icon: Plug },
      { id: "audit", label: "Audit Trail", icon: ScrollText },
    ],
  },
];

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, activePage, setActivePage, notificationCount, setWelcomeOpen } = useAppStore();
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <motion.aside
        initial={false}
        animate={{ width: sidebarCollapsed ? 76 : 268 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="glass-strong relative z-20 flex h-full shrink-0 flex-col border-r"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        {/* Logo */}
        <div className="flex h-[72px] items-center px-5" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="relative flex h-9 w-9 shrink-0 items-center justify-center">
              <AgentCore size={36} state="idle" />
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ duration: 0.2 }}
                  className="flex min-w-0 flex-col"
                >
                  <span
                    className="text-display truncate text-[15px] font-semibold leading-tight"
                    style={{ color: "var(--text-primary)" }}
                  >
                    Quality AI
                  </span>
                  <span
                    className="truncate font-mono text-[9.5px] font-medium uppercase tracking-[0.18em]"
                    style={{ color: "var(--text-muted)" }}
                  >
                    Intelligence
                  </span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* System Status */}
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="px-3 pb-1 pt-3"
            >
              <div
                className="edge-glow relative flex items-center gap-2.5 overflow-hidden rounded-lg px-3 py-2"
                style={{
                  background: "linear-gradient(180deg, rgba(16,185,129,0.09), rgba(16,185,129,0.03))",
                  border: "1px solid rgba(16,185,129,0.16)",
                }}
              >
                <div className="live-dot" style={{ width: 6, height: 6 }} />
                <span className="text-[11px] font-medium" style={{ color: "var(--success-text)" }}>
                  All Systems Operational
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {navSections.map((group, groupIndex) => (
            <div key={group.section} className={groupIndex > 0 ? "mt-5" : ""}>
              {!sidebarCollapsed ? (
                <div className="px-3 pb-2">
                  <span className="section-label text-[9.5px]" style={{ color: "var(--text-ghost)" }}>
                    {group.section}
                  </span>
                </div>
              ) : (
                groupIndex > 0 && (
                  <div className="mx-2 mb-2 h-px" style={{ background: "var(--border-subtle)" }} />
                )
              )}

              <div className="space-y-1">
                {group.items.map((item) => {
                  const isActive = activePage === item.id;
                  const badge = item.badgeFromStore ? notificationCount : undefined;
                  return (
                    <motion.button
                      key={item.id}
                      onClick={() => setActivePage(item.id)}
                      whileTap={{ scale: 0.98 }}
                      className={cn(
                        "group relative flex w-full cursor-pointer items-center rounded-xl transition-colors duration-150",
                        sidebarCollapsed ? "justify-center px-2 py-3" : "gap-3 px-3.5 py-[10px]"
                      )}
                      style={{
                        color: isActive ? "var(--accent-bright)" : "var(--text-secondary)",
                      }}
                      title={sidebarCollapsed ? item.label : undefined}
                    >
                      {isActive && (
                        <motion.div
                          layoutId="sidebar-active"
                          className="absolute inset-0 rounded-xl"
                          style={{
                            background: "linear-gradient(90deg, rgba(78,140,255,0.18), rgba(139,92,246,0.07))",
                            border: "1px solid rgba(78,140,255,0.22)",
                            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 0 24px -6px rgba(78,140,255,0.4)",
                          }}
                          transition={{ type: "spring", stiffness: 380, damping: 32 }}
                        />
                      )}
                      {isActive && !sidebarCollapsed && (
                        <motion.div
                          layoutId="sidebar-active-bar"
                          className="absolute left-0 top-1/2 h-4 w-[2.5px] -translate-y-1/2 rounded-full"
                          style={{ background: "var(--accent)", boxShadow: "0 0 8px rgba(78,140,255,0.9)" }}
                          transition={{ type: "spring", stiffness: 380, damping: 32 }}
                        />
                      )}
                      <span
                        className="relative z-10 flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-[8px] transition-all duration-150 group-hover:scale-[1.06]"
                        style={{
                          background: isActive ? "var(--accent-bg-strong)" : "rgba(148,163,184,0.05)",
                          border: `1px solid ${isActive ? "rgba(78,140,255,0.4)" : "var(--border-subtle)"}`,
                          color: isActive ? "var(--accent-bright)" : item.ai ? "var(--accent-ai-bright)" : "var(--text-secondary)",
                          boxShadow: isActive ? "0 0 16px -4px rgba(78,140,255,0.55), inset 0 1px 0 rgba(255,255,255,0.06)" : "none",
                        }}
                      >
                        <item.icon size={15} strokeWidth={2} />
                      </span>
                      <AnimatePresence>
                        {!sidebarCollapsed && (
                          <motion.span
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className={cn("relative z-10 whitespace-nowrap pl-[2px] pr-2 text-[13px]", isActive ? "font-semibold" : "font-medium")}
                          >
                            {item.label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                      {!!badge && badge > 0 && !sidebarCollapsed && (
                        <motion.span
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="relative z-10 ml-auto flex h-[18px] min-w-[18px] items-center justify-center rounded-full px-1 font-mono text-[10px] font-bold"
                          style={{
                            background: "var(--critical)",
                            color: "white",
                            boxShadow: "0 0 12px -2px rgba(239,68,68,0.8)",
                          }}
                        >
                          {badge}
                        </motion.span>
                      )}
                      {!!badge && badge > 0 && sidebarCollapsed && (
                        <span
                          className="absolute right-1 top-1 h-2 w-2 rounded-full"
                          style={{ background: "var(--critical)", boxShadow: "0 0 8px rgba(239,68,68,0.9)" }}
                        />
                      )}
                    </motion.button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Active Agents */}
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-3 pb-2"
            >
              <div className="px-2 pb-2">
                <span className="section-label text-[9.5px]" style={{ color: "var(--text-ghost)" }}>
                  Active Agents
                </span>
              </div>
              <div
                className="space-y-1.5 rounded-xl border p-2.5"
                style={{ borderColor: "var(--border-subtle)", background: "rgba(9,13,20,0.55)" }}
              >
                {[
                  { name: "SPC Monitor", detail: "streaming", icon: Wifi },
                  { name: "Alert Engine", detail: "armed", icon: AlertTriangle },
                ].map((agent) => (
                  <div key={agent.name} className="flex items-center gap-2.5 px-1 py-0.5">
                    <div className="live-dot" style={{ width: 5, height: 5 }} />
                    <span className="truncate text-[11.5px] font-medium" style={{ color: "var(--text-secondary)" }}>
                      {agent.name}
                    </span>
                    <span
                      className="ml-auto font-mono text-[9px] uppercase tracking-widest"
                      style={{ color: "var(--text-ghost)" }}
                    >
                      {agent.detail}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Bottom nav */}
        <div className="space-y-0.5 border-t px-2 py-2" style={{ borderColor: "var(--border-subtle)" }}>
          <button
            onClick={() => setSettingsOpen(true)}
            className={cn(
              "flex w-full cursor-pointer items-center rounded-lg transition-colors duration-150 hover:bg-[var(--bg-elevated)]",
              sidebarCollapsed ? "justify-center px-2 py-2.5" : "gap-2.5 px-3 py-2"
            )}
            style={{ color: "var(--text-muted)" }}
            title={sidebarCollapsed ? "Settings" : undefined}
          >
            <Settings size={15} className="shrink-0" />
            {!sidebarCollapsed && <span className="truncate text-[12px]">Settings</span>}
          </button>
          <button
            onClick={() => setWelcomeOpen(true)}
            className={cn(
              "flex w-full cursor-pointer items-center rounded-lg transition-colors duration-150 hover:bg-[var(--bg-elevated)]",
              sidebarCollapsed ? "justify-center px-2 py-2.5" : "gap-2.5 px-3 py-2"
            )}
            style={{ color: "var(--text-muted)" }}
            title={sidebarCollapsed ? "Getting started" : undefined}
          >
            <HelpCircle size={15} className="shrink-0" />
            {!sidebarCollapsed && <span className="truncate text-[12px]">Getting started</span>}
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={toggleSidebar}
          className="absolute -right-3 top-[72px] z-30 flex h-6 w-6 cursor-pointer items-center justify-center rounded-full border transition-colors hover:border-[var(--border-accent)]"
          style={{
            background: "var(--bg-elevated)",
            borderColor: "var(--border-strong)",
            color: "var(--text-muted)",
            boxShadow: "var(--shadow-sm)",
          }}
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>
      </motion.aside>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}
