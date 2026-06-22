"use client";

import { useState, useEffect, useMemo } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sparkles,
  Search,
  Volume2,
  VolumeX,
  Activity,
  TrendingUp,
  X,
  Info,
  Loader2
} from "lucide-react";
import { getAlerts, recordAlertFeedback, resolveAlert, showToast, type AlertItem } from "@/api/apiClient";
import { useRealtimeStream } from "@/api/realtime";
import { parseApiDate } from "@/lib/utils";

function formatTimeAgo(dateString: string) {
  const date = parseApiDate(dateString);
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} mins ago`;
  if (hours < 24) return `${hours} hours ago`;
  return `${days} days ago`;
}

function isToday(dateString: string | null | undefined) {
  if (!dateString) return false;
  const date = parseApiDate(dateString);
  const today = new Date();
  return date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear();
}

function AlertIcon({ type }: { type: string }) {
  if (type === "grr_fail") return <AlertTriangle size={18} style={{ color: "var(--warning)" }} />;
  if (type === "spc_violation") return <Activity size={18} style={{ color: "var(--critical-text)" }} />;
  if (type === "trend_detected") return <TrendingUp size={18} style={{ color: "var(--accent-bright)" }} />;
  return <Info size={18} style={{ color: "var(--text-muted)" }} />;
}

function SeverityBadge({ severity }: { severity: string }) {
  const classes: Record<string, string> = {
    critical: "badge-critical",
    high: "badge-warning",
    medium: "badge-warning",
    low: "badge-info",
  };
  return <span className={`badge ${classes[severity.toLowerCase()] || "badge-neutral"}`}>{severity}</span>;
}

function FilterGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div
      className="flex flex-wrap gap-1 rounded-lg border p-1"
      style={{ borderColor: "var(--border-default)", background: "rgba(9,13,20,0.6)" }}
    >
      {options.map((option) => (
        <button
          key={option}
          onClick={() => onChange(option)}
          className={`cursor-pointer whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-semibold capitalize transition-all duration-150 ${value !== option ? "hover:bg-[rgba(255,255,255,0.04)]" : ""}`}
          style={
            value === option
              ? {
                  background: "var(--bg-active)",
                  color: "var(--text-primary)",
                  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 1px 3px rgba(2,6,18,0.5)",
                }
              : { color: "var(--text-muted)" }
          }
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function HeaderStat({ value, label, tone }: { value: number; label: string; tone: string }) {
  return (
    <div className="panel-inset flex min-w-[92px] flex-col items-center justify-center rounded-xl px-4 py-2.5">
      <span className="stat-number text-xl" style={{ color: tone }}>
        {value}
      </span>
      <span className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.14em]" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
    </div>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "resolved">("all");
  const [severityFilter, setSeverityFilter] = useState<"all" | "critical" | "high" | "medium" | "low">("all");
  const [search, setSearch] = useState("");
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);

  const fetchAlerts = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      // The API caps the page size at 50.
      const res = await getAlerts({ limit: 50 });
      setAlerts(res.items);
    } catch (e) {
      console.error(e);
      if (!silent) showToast("Failed to fetch alerts");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  useRealtimeStream({
    onEvent: (event) => {
      const eventType = String(event.type || "");
      if (eventType === "alert.created" || eventType === "dlq.fallback" || eventType === "poll.tick") {
        void fetchAlerts(true);
        if (soundEnabled && eventType === "alert.created" && typeof event.message === "string") {
          showToast(`New Alert: ${event.message}`);
        }
      }
    },
  });

  const handleResolve = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await resolveAlert(id);
      showToast("Alert resolved successfully");
      fetchAlerts(true);
      if (selectedAlert?.id === id) {
        setSelectedAlert(prev => prev ? { ...prev, status: "resolved", resolved_at: new Date().toISOString() } : null);
      }
    } catch (e) {
      // toast shown by interceptor
    }
  };

  const handleFeedback = async (alert: AlertItem, isRelevant: boolean) => {
    try {
      await recordAlertFeedback(alert.id, {
        is_relevant: isRelevant,
        category: isRelevant ? "true_positive" : "false_positive",
        submitted_by: "quality-engineer",
      });
      showToast(isRelevant ? "Alert marked relevant." : "Alert marked false positive.");
    } catch (e) {
      // toast shown by interceptor
    }
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter(a => {
      if (statusFilter !== "all" && a.status !== statusFilter) return false;
      if (severityFilter !== "all" && a.severity !== severityFilter) return false;
      if (search && !a.message.toLowerCase().includes(search.toLowerCase()) && !a.process_name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [alerts, statusFilter, severityFilter, search]);

  const stats = useMemo(() => {
    return {
      active: alerts.filter(a => a.status === "active").length,
      critical: alerts.filter(a => a.status === "active" && a.severity === "critical").length,
      resolvedToday: alerts.filter(a => a.status === "resolved" && isToday(a.resolved_at)).length,
    };
  }, [alerts]);

  return (
    <div className="h-full overflow-y-auto px-4 py-6 md:px-6" style={{ color: "var(--text-primary)" }}>
      <div className="mx-auto flex max-w-6xl flex-col gap-5">

        {/* Header & Stats Bar */}
        <header className="surface-card edge-glow px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-4">
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-xl border"
                  style={{
                    borderColor: "rgba(239,68,68,0.22)",
                    background: "var(--critical-bg)",
                    color: "var(--critical-text)",
                    boxShadow: "0 0 24px -6px rgba(239,68,68,0.45), inset 0 1px 0 rgba(255,255,255,0.06)",
                  }}
                >
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <h1 className="page-title md:text-[26px]">Alert Inbox</h1>
                  <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                    Proactive quality alerting — violations, trends, and escalations in one queue.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 text-sm">
              <HeaderStat value={stats.active} label="Active" tone="var(--warning-text)" />
              <HeaderStat value={stats.critical} label="Critical" tone="var(--critical-text)" />
              <HeaderStat value={stats.resolvedToday} label="Resolved Today" tone="var(--success-text)" />
            </div>
          </div>
        </header>

        {/* Filters */}
        <div className="surface-card flex flex-col gap-4 px-5 py-3.5 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <FilterGroup
              options={["all", "active", "resolved"] as const}
              value={statusFilter}
              onChange={(v) => setStatusFilter(v)}
            />

            <div className="hidden h-6 w-px sm:block" style={{ background: "var(--border-strong)" }} />

            <FilterGroup
              options={["all", "critical", "high", "medium", "low"] as const}
              value={severityFilter}
              onChange={(v) => setSeverityFilter(v)}
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search alerts…"
                className="input-field w-full py-2 pl-8 pr-4 text-xs sm:w-52"
              />
            </div>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="btn-icon h-9 w-9 shrink-0 cursor-pointer"
              title={soundEnabled ? "Mute Notifications" : "Unmute Notifications"}
            >
              {soundEnabled ? <Volume2 size={15} /> : <VolumeX size={15} />}
            </button>
          </div>
        </div>

        {/* Alert List */}
        <div className="grid gap-3">
          {loading && alerts.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-center" style={{ color: "var(--text-muted)" }}>
              <Loader2 size={24} className="mb-2 animate-spin" />
              Loading alerts…
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div
              className="rounded-xl border border-dashed py-12 text-center"
              style={{ borderColor: "var(--border-strong)", background: "rgba(9,13,20,0.5)", color: "var(--text-muted)" }}
            >
              No alerts found matching the current filters.
            </div>
          ) : (
            filteredAlerts.map(alert => (
              <div
                key={alert.id}
                className="surface-card group flex flex-col justify-between gap-4 p-4 sm:flex-row sm:items-center"
                style={
                  alert.status === "active" && alert.severity === "critical"
                    ? { boxShadow: "inset 2.5px 0 0 var(--critical), var(--shadow-sm)" }
                    : alert.status === "active" && alert.severity === "high"
                      ? { boxShadow: "inset 2.5px 0 0 var(--warning), var(--shadow-sm)" }
                      : undefined
                }
              >
                <div className="flex items-start gap-4">
                  <div className="mt-1">
                    <AlertIcon type={alert.type} />
                  </div>
                  <div>
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={alert.severity} />
                      <span className="font-mono text-[10.5px] uppercase tracking-[0.1em]" style={{ color: "var(--text-muted)" }}>
                        {alert.process_name}
                      </span>
                      {alert.status === "resolved" && (
                        <span className="badge badge-success">Resolved</span>
                      )}
                    </div>
                    <div className="line-clamp-2 max-w-2xl text-sm font-medium leading-relaxed" style={{ color: "var(--text-primary)" }}>
                      {alert.message}
                    </div>
                    <div className="mt-2 flex items-center gap-1.5 text-[11px]" style={{ color: "var(--text-muted)" }}>
                      <Clock size={11} />
                      <span>{formatTimeAgo(alert.created_at)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2 sm:ml-auto">
                  {alert.status === "active" && (
                    <button onClick={(e) => handleResolve(alert.id, e)} className="btn btn-success h-8 cursor-pointer px-3 text-xs">
                      <CheckCircle2 size={13} /> Resolve
                    </button>
                  )}
                  <button onClick={() => setSelectedAlert(alert)} className="btn btn-secondary h-8 cursor-pointer px-3 text-xs">
                    <Info size={13} /> Details
                  </button>
                  <button
                    onClick={() => void handleFeedback(alert, true)}
                    className="btn h-8 cursor-pointer px-3 text-xs"
                    style={{ background: "var(--info-bg)", borderColor: "rgba(78,140,255,0.3)", color: "var(--info-text)" }}
                  >
                    Relevant
                  </button>
                  <button onClick={() => void handleFeedback(alert, false)} className="btn btn-danger h-8 cursor-pointer px-3 text-xs">
                    False Positive
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {selectedAlert && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(2,5,12,0.72)", backdropFilter: "blur(6px)" }}
          onClick={() => setSelectedAlert(null)}
        >
          <div
            className="glass-overlay flex max-h-[90vh] w-full max-w-lg flex-col rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b p-5" style={{ borderColor: "var(--border-subtle)" }}>
              <h2 className="text-display flex items-center gap-2.5 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                <AlertIcon type={selectedAlert.type} /> Alert Details
              </h2>
              <button onClick={() => setSelectedAlert(null)} className="btn-icon h-8 w-8 cursor-pointer" aria-label="Close details">
                <X size={16} />
              </button>
            </div>

            <div className="space-y-6 overflow-y-auto p-5">
              <div className="flex gap-2">
                <SeverityBadge severity={selectedAlert.severity} />
                <span className={`badge ${selectedAlert.status === "resolved" ? "badge-success" : "badge-warning"}`}>
                  {selectedAlert.status}
                </span>
              </div>

              <div>
                <div className="section-label mb-1 text-[10px]">Process</div>
                <div className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                  {selectedAlert.process_name}
                </div>
              </div>

              <div>
                <div className="section-label mb-1.5 text-[10px]">Message</div>
                <div className="panel-inset p-4 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {selectedAlert.message}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="section-label mb-1 text-[10px]">Created</div>
                  <div className="flex items-center gap-1.5 text-sm" style={{ color: "var(--text-secondary)" }}>
                    <Clock size={13} style={{ color: "var(--text-muted)" }} />
                    {parseApiDate(selectedAlert.created_at).toLocaleString()}
                  </div>
                </div>
                {selectedAlert.resolved_at && (
                  <div>
                    <div className="section-label mb-1 text-[10px]">Resolved</div>
                    <div className="flex items-center gap-1.5 text-sm" style={{ color: "var(--text-secondary)" }}>
                      <CheckCircle2 size={13} style={{ color: "var(--success)" }} />
                      {parseApiDate(selectedAlert.resolved_at).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              <div>
                <div className="section-label mb-2 flex items-center gap-2 text-[10px]">
                  <Sparkles size={13} style={{ color: "var(--accent-ai-bright)" }} /> AI Analysis
                </div>
                <div
                  className="rounded-xl border p-4 text-sm leading-relaxed"
                  style={{
                    borderColor: "rgba(139,92,246,0.18)",
                    background: "linear-gradient(180deg, rgba(139,92,246,0.07), rgba(139,92,246,0.02))",
                    color: "var(--text-secondary)",
                  }}
                >
                  This alert was triggered by the automated monitoring system based on the severity and specific rules configured for{" "}
                  <code
                    className="rounded px-1 font-mono text-[12px]"
                    style={{ color: "var(--accent-ai-bright)", background: "var(--accent-ai-bg)" }}
                  >
                    {selectedAlert.process_name}
                  </code>
                  .
                  <br />
                  <br />
                  <strong style={{ color: "var(--text-primary)" }}>Recommendation:</strong> Investigate the root cause immediately to
                  ensure quality standards are met. If this is a recurring issue, consider adjusting the process control limits or
                  retraining operators.
                </div>
              </div>
            </div>

            <div
              className="flex flex-wrap justify-end gap-2.5 rounded-b-2xl border-t p-4"
              style={{ borderColor: "var(--border-subtle)", background: "rgba(9,13,20,0.6)" }}
            >
              <button onClick={() => setSelectedAlert(null)} className="btn btn-ghost cursor-pointer">
                Close
              </button>
              {selectedAlert.status === "active" && (
                <button onClick={(e) => handleResolve(selectedAlert.id, e)} className="btn btn-success cursor-pointer">
                  <CheckCircle2 size={15} /> Resolve Alert
                </button>
              )}
              <button
                onClick={() => void handleFeedback(selectedAlert, true)}
                className="btn cursor-pointer"
                style={{ background: "var(--info-bg)", borderColor: "rgba(78,140,255,0.3)", color: "var(--info-text)" }}
              >
                Relevant
              </button>
              <button onClick={() => void handleFeedback(selectedAlert, false)} className="btn btn-danger cursor-pointer">
                False Positive
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
