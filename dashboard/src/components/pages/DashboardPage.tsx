"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Activity,
  TrendingUp,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getAlerts,
  getAuditLog,
  getDashboardSummary,
  getGRRHistory,
  resolveAlert,
  showToast,
  type AlertItem,
  type AlertListResponse,
  type AuditLogItem,
  type DashboardSummaryResponse,
  type GRRHistoryItem,
} from "@/api/apiClient";
import { useRealtimeStream } from "@/api/realtime";
import { parseApiDate, spotlightMove } from "@/lib/utils";

type DashboardPayload = {
  summary: DashboardSummaryResponse;
  grrHistory: GRRHistoryItem[];
  alerts: AlertListResponse;
  auditLog: AuditLogItem[];
};

const SEVERITY_ORDER: Record<AlertItem["severity"], number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

const VERDICT_LABELS: Record<GRRHistoryItem["verdict"], string> = {
  pass: "Excellent",
  acceptable: "Acceptable",
  fail: "Unacceptable",
};

const VERDICT_STYLES: Record<GRRHistoryItem["verdict"], string> = {
  pass: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
  acceptable: "bg-amber-500/15 text-amber-300 border-amber-500/25",
  fail: "bg-rose-500/15 text-rose-300 border-rose-500/25",
};

const VERDICT_DOT: Record<GRRHistoryItem["verdict"], string> = {
  pass: "#34d399",
  acceptable: "#fbbf24",
  fail: "#f87171",
};

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.07, delayChildren: 0.1 } },
};
const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 380, damping: 28 } },
};

function formatTimestamp(value?: string | null) {
  if (!value) return "—";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatShortDate(value?: string | null) {
  if (!value) return "";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}

function formatRelativeTrend(current: number, previous: number) {
  if (!previous) return { label: "New baseline", direction: "flat" as const };
  const delta = ((current - previous) / previous) * 100;
  if (Math.abs(delta) < 1) return { label: "Flat vs last week", direction: "flat" as const };
  return {
    label: `${delta > 0 ? "+" : ""}${delta.toFixed(0)}% vs last week`,
    direction: delta > 0 ? ("up" as const) : ("down" as const),
  };
}

function getPassRateTone(passRate: number) {
  if (passRate > 70) return "text-emerald-300 border-emerald-500/25 bg-emerald-500/10";
  if (passRate >= 40) return "text-amber-300 border-amber-500/25 bg-amber-500/10";
  return "text-rose-300 border-rose-500/25 bg-rose-500/10";
}

function getSeverityTone(severity?: AlertItem["severity"]) {
  switch (severity) {
    case "critical": return "text-rose-300 bg-rose-500/10 border-rose-500/20";
    case "high": return "text-orange-300 bg-orange-500/10 border-orange-500/20";
    case "medium": return "text-amber-300 bg-amber-500/10 border-amber-500/20";
    default: return "text-sky-300 bg-sky-500/10 border-sky-500/20";
  }
}

function isWithinDays(timestamp: string, days: number, referenceTime: number) {
  const date = parseApiDate(timestamp);
  if (Number.isNaN(date.getTime())) return false;
  return referenceTime - date.getTime() <= days * 24 * 60 * 60 * 1000;
}

function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`shimmer-loading rounded-xl ${className}`} />;
}

function GrrTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { date: string; value: number; verdict: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const pt = payload[0].payload;
  return (
    <div className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-elevated)] px-3 py-2 text-xs shadow-xl">
      <div className="font-semibold text-[var(--text-primary)]">{pt.value.toFixed(2)}%</div>
      <div className="mt-0.5 text-[var(--text-muted)]">{pt.date} · {pt.verdict}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const loadDashboard = useCallback(async () => {
    if (hasLoadedOnce) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);
    try {
      const [summary, grrHistory, alerts, auditLog] = await Promise.all([
        getDashboardSummary(),
        getGRRHistory(),
        getAlerts({ status: "active", limit: 50 }),
        getAuditLog(),
      ]);
      setData({ summary, grrHistory, alerts, auditLog });
      setHasLoadedOnce(true);
      setLastUpdated(new Date());
      setNow(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [hasLoadedOnce]);

  useEffect(() => { void loadDashboard(); }, [loadDashboard]);

  useRealtimeStream({
    onEvent: (event) => {
      const t = String(event.type || "");
      if (["measurement.processed", "spc.analysis", "grr.analysis", "alert.created", "mes.event", "qms.event", "poll.tick"].includes(t)) {
        void loadDashboard();
      }
    },
  });

  const handleResolveAlert = useCallback(async (alertId: string) => {
    setResolvingId(alertId);
    try {
      await resolveAlert(alertId);
      await loadDashboard();
    } finally {
      setResolvingId(null);
    }
  }, [loadDashboard]);

  const summary = data?.summary;
  const grrHistory = data?.grrHistory ?? [];
  const activeAlerts = [...(data?.alerts.items ?? [])].sort(
    (a, b) => SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity]
  );
  const auditPreview = (data?.auditLog ?? []).slice(0, 5);

  const totalThisWeek = grrHistory.filter((item) => isWithinDays(item.timestamp, 7, now)).length;
  const totalPrevWeek = grrHistory.filter((item) => {
    const age = now - parseApiDate(item.timestamp).getTime();
    return age > 7 * 24 * 60 * 60 * 1000 && age <= 14 * 24 * 60 * 60 * 1000;
  }).length;
  const totalTrend = formatRelativeTrend(totalThisWeek, totalPrevWeek);

  const processesMonitored = useMemo(() => {
    const names = new Set<string>();
    for (const alert of activeAlerts) { if (alert.process_name) names.add(alert.process_name); }
    for (const entry of auditPreview) { if (entry.entity_type === "spc_process" && entry.entity_id) names.add(entry.entity_id); }
    return names.size;
  }, [activeAlerts, auditPreview]);

  const highestSeverity = activeAlerts[0]?.severity;
  const passRate = summary?.passing_rate ?? 0;
  const passRateTone = getPassRateTone(passRate);
  const showInitialLoading = loading && !data;
  const hasInitialError = error && !data;

  const grrChartData = grrHistory
    .filter((item) => item.grr_percent != null)
    .slice(-20)
    .map((item) => ({
      date: formatShortDate(item.timestamp),
      value: item.grr_percent!,
      verdict: VERDICT_LABELS[item.verdict],
      fill: VERDICT_DOT[item.verdict],
    }));

  if (hasInitialError) {
    return (
      <div className="min-h-full px-6 py-8 text-[var(--text-primary)]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-auto flex max-w-md items-center justify-center rounded-2xl border border-[var(--critical-bg)] bg-[var(--bg-surface)] p-8 shadow-2xl"
        >
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-500/10 text-rose-300">
              <AlertTriangle size={22} />
            </div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Dashboard unavailable</h1>
            <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">{error}</p>
            <button
              onClick={() => void loadDashboard()}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[var(--success)] px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:opacity-90"
            >
              <RefreshCw size={16} /> Retry
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto text-[var(--text-primary)]">
      <div className="mx-auto flex min-h-full max-w-[1640px] flex-col gap-7 px-6 py-7 lg:gap-8 lg:px-10 lg:py-9">

        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 240, damping: 30 }}
          className="surface-card px-7 py-7 lg:px-9 lg:py-8"
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <div className="kicker mb-4" style={{ color: "var(--accent-bright)" }}>
                <span className="live-dot" style={{ width: 6, height: 6 }} />
                Autonomous Quality Intelligence
              </div>
              <h1 className="text-display gradient-text text-[30px] font-semibold leading-[1.08] md:text-[38px]">
                Quality Control AI Agent
              </h1>
              <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-[var(--text-secondary)]">
                Autonomous GR&amp;R analysis, real-time SPC monitoring, and proactive
                alerting — one precision instrument for your production line.
              </p>

              <div className="mt-6 flex flex-wrap items-center gap-2.5">
                <HeroChip icon={<CheckCircle2 size={13} />} tone="success">
                  {passRate.toFixed(1)}% pass rate
                </HeroChip>
                <HeroChip icon={<Activity size={13} />} tone="info">
                  {processesMonitored} processes monitored
                </HeroChip>
                <HeroChip
                  icon={<ShieldAlert size={13} />}
                  tone={(summary?.active_alerts_count ?? 0) > 0 ? "critical" : "muted"}
                >
                  {summary?.active_alerts_count ?? 0} active alerts
                </HeroChip>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-3">
              {refreshing && <Loader2 size={14} className="animate-spin text-[var(--text-muted)]" />}
              <div className="panel-inset rounded-xl px-5 py-3.5">
                <div className="flex items-center gap-1.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.16em] text-[var(--text-muted)]">
                  <Clock3 size={11} /> Last updated
                </div>
                <div className="stat-number mt-1 text-sm text-[var(--text-primary)]">
                  {lastUpdated ? formatTimestamp(lastUpdated.toISOString()) : "Waiting…"}
                </div>
              </div>
              <button
                onClick={() => void loadDashboard()}
                className="btn-icon h-11 w-11 cursor-pointer rounded-2xl"
                title="Refresh"
              >
                <RefreshCw size={15} />
              </button>
            </div>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-6 flex items-center justify-between gap-3 overflow-hidden rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200"
              >
                <span>{error}</span>
                <button
                  onClick={() => void loadDashboard()}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-1.5 text-xs font-semibold text-amber-100 transition hover:bg-amber-400/20"
                >
                  <RefreshCw size={12} /> Retry
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.header>

        {/* Stat cards */}
        <motion.section
          className="grid gap-5 md:grid-cols-2 xl:grid-cols-4"
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
          <motion.div variants={cardVariants}>
            <StatCard
              title="Total GR&R Analyses"
              value={summary?.total_grr_analyses ?? 0}
              icon={<Database size={17} />}
              tone="text-[var(--text-primary)]"
              accent="border-[var(--accent-bg-strong)] bg-[var(--accent-bg)] text-[var(--accent)]"
              detail={totalTrend.label}
              trend={totalTrend.direction}
              loading={showInitialLoading}
            />
          </motion.div>
          <motion.div variants={cardVariants}>
            <StatCard
              title="Current Pass Rate"
              value={`${passRate.toFixed(1)}%`}
              icon={<CheckCircle2 size={17} />}
              tone={passRateTone.split(" ")[0]}
              accent={passRateTone}
              detail={passRate > 70 ? "Healthy process capability" : passRate >= 40 ? "Review recommended" : "Immediate attention required"}
              loading={showInitialLoading}
            />
          </motion.div>
          <motion.div variants={cardVariants}>
            <StatCard
              title="Active Alerts"
              value={summary?.active_alerts_count ?? 0}
              icon={<AlertTriangle size={17} />}
              tone="text-[var(--text-primary)]"
              accent={getSeverityTone(highestSeverity)}
              detail={highestSeverity ? `Highest severity: ${highestSeverity}` : "No active incidents"}
              loading={showInitialLoading}
            />
          </motion.div>
          <motion.div variants={cardVariants}>
            <StatCard
              title="Processes Monitored"
              value={processesMonitored}
              icon={<Activity size={17} />}
              tone="text-[var(--text-primary)]"
              accent="border-[var(--border-strong)] bg-[var(--bg-elevated)] text-[var(--text-secondary)]"
              detail="Tracked via alerts and audit trail"
              loading={showInitialLoading}
            />
          </motion.div>
        </motion.section>

        {/* Main panels */}
        <section className="grid gap-6 xl:grid-cols-2">
          <Panel title="Recent GR&R Results" icon={<Database size={15} />}>
            {showInitialLoading ? (
              <TableSkeleton rows={8} />
            ) : (
              <div className="overflow-hidden rounded-xl border border-[var(--border-default)]">
                <table className="min-w-full divide-y divide-[var(--border-subtle)] text-left text-sm">
                  <thead className="bg-[var(--bg-elevated)] text-[10px] uppercase tracking-widest text-[var(--text-muted)]">
                    <tr>
                      <th className="px-4 py-3 font-medium">Timestamp</th>
                      <th className="px-4 py-3 font-medium">GR&R %</th>
                      <th className="px-4 py-3 font-medium">Verdict</th>
                      <th className="px-4 py-3 font-medium">Operators</th>
                      <th className="px-4 py-3 font-medium">Parts</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-root)]/40">
                    {grrHistory.slice(0, 10).map((item) => (
                      <tr key={item.id} className="transition hover:bg-[var(--bg-hover)]">
                        <td className="px-4 py-3 text-[var(--text-muted)]">{formatTimestamp(item.timestamp)}</td>
                        <td className="px-4 py-3 font-semibold tabular-nums text-[var(--text-primary)]">
                          {item.grr_percent?.toFixed(1) ?? "—"}%
                        </td>
                        <td className="px-4 py-3">
                          <span className={`badge ${
                            item.verdict === "pass" ? "badge-success" : item.verdict === "acceptable" ? "badge-warning" : "badge-critical"
                          }`}>
                            {VERDICT_LABELS[item.verdict]}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[var(--text-secondary)]">{item.operator_count}</td>
                        <td className="px-4 py-3 text-[var(--text-secondary)]">{item.part_count}</td>
                      </tr>
                    ))}
                    {!grrHistory.length && (
                      <tr>
                        <td className="px-4 py-8 text-center text-[var(--text-muted)]" colSpan={5}>
                          No GR&R analyses available.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          <Panel title="Active Alerts" icon={<ShieldAlert size={15} />}>
            {showInitialLoading ? (
              <ListSkeleton rows={5} />
            ) : activeAlerts.length ? (
              <div className="space-y-2.5">
                <AnimatePresence initial={false}>
                  {activeAlerts.map((alert) => (
                    <motion.div
                      key={alert.id}
                      initial={{ opacity: 0, x: 8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -8 }}
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                      className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 transition hover:border-[var(--border-strong)] hover:bg-[var(--bg-elevated)]"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`badge ${getSeverityTone(alert.severity).includes("rose") ? "badge-critical" : getSeverityTone(alert.severity).includes("amber") ? "badge-warning" : "badge-info"}`}>
                              {alert.severity}
                            </span>
                            {alert.process_name && (
                              <span className="text-[10px] uppercase tracking-widest text-[var(--text-muted)]">
                                {alert.process_name}
                              </span>
                            )}
                          </div>
                          <p className="mt-2 text-sm leading-relaxed text-[var(--text-primary)]">{alert.message}</p>
                          <p className="mt-1 text-xs text-[var(--text-muted)]">{formatTimestamp(alert.created_at)}</p>
                        </div>
                        <button
                          onClick={() => void handleResolveAlert(alert.id)}
                          disabled={resolvingId === alert.id}
                          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[var(--success-bg)] bg-[var(--success-bg)] px-3 py-1.5 text-xs font-semibold text-[var(--success)] transition hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {resolvingId === alert.id
                            ? <Loader2 size={12} className="animate-spin" />
                            : <CheckCircle2 size={12} />}
                          Resolve
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            ) : (
              <EmptyState
                icon={<CheckCircle2 size={18} />}
                title="No active alerts"
                description="All monitored processes are within control limits."
              />
            )}
          </Panel>
        </section>

        {/* Charts row */}
        <section className="grid gap-6 xl:grid-cols-2">
          <Panel title="GR&R Trend (Last 20 Runs)" icon={<TrendingUp size={15} />}>
            {showInitialLoading ? (
              <SkeletonBlock className="h-[280px]" />
            ) : grrChartData.length > 1 ? (
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={grrChartData} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                      unit="%"
                      domain={[0, "auto"]}
                    />
                    <Tooltip content={<GrrTooltip />} />
                    <ReferenceLine
                      y={30}
                      stroke="var(--critical)"
                      strokeDasharray="4 4"
                      strokeOpacity={0.5}
                      label={{ value: "30% limit", fill: "var(--critical)", fontSize: 9, position: "right" }}
                    />
                    <ReferenceLine
                      y={10}
                      stroke="var(--success)"
                      strokeDasharray="4 4"
                      strokeOpacity={0.5}
                      label={{ value: "10% target", fill: "var(--success)", fontSize: 9, position: "right" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="var(--accent)"
                      strokeWidth={2}
                      dot={({ cx, cy, payload }) => (
                        <circle
                          key={`dot-${cx}-${cy}`}
                          cx={cx}
                          cy={cy}
                          r={4}
                          fill={(payload as { fill: string }).fill}
                          stroke="var(--bg-root)"
                          strokeWidth={1.5}
                        />
                      )}
                      activeDot={{ r: 5, fill: "var(--accent-bright)", stroke: "var(--bg-root)", strokeWidth: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState
                icon={<TrendingUp size={18} />}
                title="No trend data yet"
                description="GR&R history will appear here after analyses are recorded."
              />
            )}
          </Panel>

          <Panel title="Audit Log" icon={<FileText size={15} />}>
            {showInitialLoading ? (
              <ListSkeleton rows={5} />
            ) : auditPreview.length ? (
              <div className="space-y-2.5">
                {auditPreview.map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-3.5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">{entry.action}</p>
                        <p className="mt-0.5 text-[10px] uppercase tracking-widest text-[var(--text-muted)]">
                          {entry.entity_type} · {entry.entity_id}
                        </p>
                      </div>
                      <span className="shrink-0 text-xs text-[var(--text-muted)]">{formatTimestamp(entry.timestamp)}</span>
                    </div>
                    <p className="mt-1.5 text-xs text-[var(--text-secondary)]">Actor: {entry.actor}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<FileText size={18} />}
                title="No audit entries"
                description="Audit logs appear here after quality workflows run."
              />
            )}
          </Panel>
        </section>
      </div>
    </div>
  );
}

function HeroChip({
  icon,
  tone,
  children,
}: {
  icon: React.ReactNode;
  tone: "success" | "info" | "critical" | "muted";
  children: React.ReactNode;
}) {
  const tones = {
    success: { c: "var(--success-text)", b: "rgba(16,185,129,0.28)", bg: "rgba(16,185,129,0.1)" },
    info: { c: "var(--accent-bright)", b: "rgba(78,140,255,0.3)", bg: "rgba(78,140,255,0.1)" },
    critical: { c: "var(--critical-text)", b: "rgba(239,68,68,0.3)", bg: "rgba(239,68,68,0.1)" },
    muted: { c: "var(--text-secondary)", b: "var(--border-strong)", bg: "rgba(148,163,184,0.06)" },
  }[tone];
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[12.5px] font-medium tabular-nums backdrop-blur-md"
      style={{ color: tones.c, borderColor: tones.b, background: tones.bg }}
    >
      {icon}
      {children}
    </span>
  );
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 28, delay: 0.15 }}
      onMouseMove={spotlightMove}
      className="surface-card spotlight p-6"
    >
      <div className="mb-5 flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] text-[var(--accent-bright)]">
          {icon}
        </div>
        <h2 className="section-label">{title}</h2>
      </div>
      {children}
    </motion.div>
  );
}

function StatCard({
  title,
  value,
  icon,
  accent,
  tone,
  detail,
  trend,
  loading,
}: {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  accent: string;
  tone: string;
  detail: string;
  trend?: "up" | "down" | "flat";
  loading: boolean;
}) {
  return (
    <motion.div
      whileHover={{ y: -3, transition: { type: "spring", stiffness: 400, damping: 20 } }}
      onMouseMove={spotlightMove}
      className="surface-card spotlight group p-6"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">{title}</p>
          {loading ? (
            <SkeletonBlock className="mt-4 h-9 w-28" />
          ) : (
            <div className={`stat-number mt-4 text-[34px] leading-none ${tone}`}>{value}</div>
          )}
        </div>
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition-transform duration-200 group-hover:scale-110 ${accent}`}
        >
          {icon}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3">
        <span className="text-xs text-[var(--text-muted)]">{detail}</span>
        {trend === "up" && (
          <span className="inline-flex items-center gap-0.5 font-mono text-[11px] font-semibold text-[var(--success-text)]">
            <ArrowUpRight size={12} /> Up
          </span>
        )}
        {trend === "down" && (
          <span className="inline-flex items-center gap-0.5 font-mono text-[11px] font-semibold text-[var(--critical-text)]">
            <ArrowDownRight size={12} /> Down
          </span>
        )}
      </div>
    </motion.div>
  );
}

function EmptyState({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center rounded-xl border border-dashed border-[var(--border-default)] bg-[var(--bg-root)]/40 px-6 py-8 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--border-default)] bg-[var(--bg-elevated)] text-[var(--text-muted)]">
        {icon}
      </div>
      <h3 className="mt-3 text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
      <p className="mt-1 max-w-xs text-xs leading-relaxed text-[var(--text-muted)]">{description}</p>
    </div>
  );
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border-default)]">
      <div className="grid grid-cols-5 gap-3 border-b border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-4 py-3">
        {Array.from({ length: 5 }).map((_, i) => <SkeletonBlock key={i} className="h-3" />)}
      </div>
      <div className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-root)]/40">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="grid grid-cols-5 gap-4 px-4 py-3.5">
            <SkeletonBlock className="h-4 w-24" />
            <SkeletonBlock className="h-4 w-14" />
            <SkeletonBlock className="h-5 w-20 rounded-full" />
            <SkeletonBlock className="h-4 w-10" />
            <SkeletonBlock className="h-4 w-10" />
          </div>
        ))}
      </div>
    </div>
  );
}

function ListSkeleton({ rows }: { rows: number }) {
  return (
    <div className="space-y-2.5">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 space-y-2.5">
              <SkeletonBlock className="h-4 w-32" />
              <SkeletonBlock className="h-3.5 w-full" />
              <SkeletonBlock className="h-3 w-20" />
            </div>
            <SkeletonBlock className="h-8 w-20 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}
