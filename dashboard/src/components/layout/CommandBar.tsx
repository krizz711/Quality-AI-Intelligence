"use client";

import { useEffect, useRef, useState } from "react";
import {
  Search,
  Sparkles,
  Bell,
  ChevronRight,
  TriangleAlert,
  LayoutDashboard,
  FlaskConical,
  ClipboardCheck,
  Activity,
  ScrollText,
  Bot,
  Ruler,
  Workflow,
  Plug,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { getDashboardSummary } from "@/api/apiClient";
import { useBackendHealth } from "@/lib/useBackendHealth";
import { useRealtimeStream } from "@/api/realtime";

const PAGE_META: Record<string, { label: string; icon: React.ComponentType<{ size?: number; className?: string }> }> = {
  dashboard: { label: "Overview", icon: LayoutDashboard },
  grr: { label: "GR&R Studies", icon: FlaskConical },
  gages: { label: "Gage Registry", icon: Ruler },
  review: { label: "Review Queue", icon: ClipboardCheck },
  spc: { label: "SPC Monitor", icon: Activity },
  alerts: { label: "Alert Inbox", icon: TriangleAlert },
  "alert-rules": { label: "Alert Rules", icon: Workflow },
  integrations: { label: "Connections", icon: Plug },
  audit: { label: "Audit Trail", icon: ScrollText },
  agent: { label: "AI Agent", icon: Bot },
};

export default function CommandBar() {
  const { activePage, notificationCount, setNotificationCount, setActivePage, setChatOpen, setPendingChatPrompt, setCommandPaletteOpen } = useAppStore();
  const [focused, setFocused] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const health = useBackendHealth();

  // Keep the alert badge honest: sync with the backend count.
  useEffect(() => {
    let cancelled = false;

    const sync = async () => {
      try {
        const summary = await getDashboardSummary();
        if (!cancelled) {
          setNotificationCount(summary.active_alerts_count);
        }
      } catch {
        // Backend offline — leave the badge at its last known value.
      }
    };

    void sync();
    return () => {
      cancelled = true;
    };
  }, [setNotificationCount]);

  useRealtimeStream({
    onEvent: (event) => {
      const t = String(event.type || "");
      if (t === "alert.created" || t === "poll.tick") {
        void getDashboardSummary()
          .then((summary) => setNotificationCount(summary.active_alerts_count))
          .catch(() => undefined);
      }
    },
  });

  // Ctrl/Cmd+K opens the command palette.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen(true);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setCommandPaletteOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedQuery = query.trim();

    if (trimmedQuery) {
      setPendingChatPrompt(trimmedQuery);
      setActivePage("agent");
      setChatOpen(true);
      setQuery("");
      inputRef.current?.blur();
    }
  };

  const page = PAGE_META[activePage] || PAGE_META.dashboard;
  const PageIcon = page.icon;

  return (
      <header
        className="glass-strong z-10 flex h-[72px] shrink-0 items-center gap-4 border-b px-7"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        {/* Breadcrumb */}
        <div className="flex min-w-0 items-center gap-2 text-sm">
          <span className="font-mono text-[11px] uppercase tracking-[0.16em]" style={{ color: "var(--text-ghost)" }}>
            Quality AI
          </span>
          <ChevronRight size={13} style={{ color: "var(--text-ghost)" }} />
          <span
            className="flex h-6 w-6 items-center justify-center rounded-md border"
            style={{
              background: "var(--accent-bg)",
              borderColor: "rgba(78,140,255,0.2)",
              color: "var(--accent-bright)",
            }}
          >
            <PageIcon size={13} />
          </span>
          <span className="text-display truncate text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {page.label}
          </span>
        </div>

        <div className="flex-1" />

        {/* Ask AI */}
        <form onSubmit={handleSubmit} className="w-[340px] max-w-[36vw]">
          <div
            className="relative flex h-10 items-center rounded-xl transition-all duration-200"
            style={{
              background: focused ? "rgba(11,17,27,0.95)" : "var(--bg-primary)",
              border: `1px solid ${focused ? "var(--accent)" : "var(--border-default)"}`,
              boxShadow: focused
                ? "var(--ring-focus), 0 0 24px -8px rgba(78,140,255,0.45)"
                : "inset 0 1px 2px rgba(2,6,18,0.4)",
            }}
          >
            {focused ? (
              <Sparkles size={14} className="ml-3 shrink-0" style={{ color: "var(--accent-ai-bright)" }} />
            ) : (
              <Search size={14} className="ml-3 shrink-0" style={{ color: "var(--text-muted)" }} />
            )}
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="Ask the quality copilot…"
              className="min-w-0 flex-1 bg-transparent px-2.5 text-[13px] outline-none"
              style={{ color: "var(--text-primary)" }}
              aria-label="Ask the AI copilot"
            />
            <kbd className="kbd mr-2 hidden sm:inline-flex">⌘K</kbd>
          </div>
        </form>

        {/* Connection state */}
        {health === "online" ? (
          <span
            className="hidden h-7 items-center gap-2 rounded-full border px-3 md:inline-flex"
            style={{ borderColor: "rgba(16,185,129,0.22)", background: "var(--success-bg)" }}
          >
            <span className="live-dot" style={{ width: 6, height: 6 }} />
            <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--success-text)" }}>
              Live
            </span>
          </span>
        ) : health === "offline" ? (
          <span
            className="hidden h-7 items-center gap-1.5 rounded-full border px-3 md:inline-flex"
            style={{ borderColor: "rgba(239,68,68,0.25)", background: "var(--critical-bg)" }}
          >
            <TriangleAlert size={12} style={{ color: "var(--critical)" }} />
            <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--critical-text)" }}>
              Offline
            </span>
          </span>
        ) : (
          <span
            className="hidden h-7 items-center gap-2 rounded-full border px-3 md:inline-flex"
            style={{ borderColor: "rgba(245,158,11,0.22)", background: "var(--warning-bg)" }}
          >
            <span className="status-dot status-dot-warning" style={{ width: 6, height: 6 }} />
            <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--warning-text)" }}>
              Connecting
            </span>
          </span>
        )}

        <button
          onClick={() => setActivePage("alerts")}
          className="btn-icon relative h-9 w-9 cursor-pointer"
          title={notificationCount > 0 ? `${notificationCount} active alerts` : "Alert inbox"}
          aria-label="Open alert inbox"
        >
          <Bell size={16} />
          {notificationCount > 0 && (
            <span
              className="absolute -right-1.5 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full px-1 font-mono text-[10px] font-bold"
              style={{
                background: "var(--critical)",
                color: "#fff",
                border: "2px solid var(--bg-root)",
                boxShadow: "0 0 12px -2px rgba(239,68,68,0.9)",
              }}
            >
              {notificationCount}
            </span>
          )}
        </button>

        <div
          className="relative flex h-9 w-9 cursor-default items-center justify-center rounded-full text-[12px] font-bold"
          style={{
            background: "var(--gradient-ai)",
            color: "#fff",
            boxShadow: "0 0 0 2px var(--bg-root), 0 0 0 3.5px rgba(139,92,246,0.45), 0 2px 12px -2px rgba(139,92,246,0.6)",
          }}
          title="Quality Engineer — Quality AI Intelligence"
        >
          QE
        </div>
      </header>
  );
}
