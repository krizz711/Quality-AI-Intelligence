"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import HelpTip from "@/components/ui/HelpTip";
import {
  Ruler,
  Plus,
  Trash2,
  FlaskConical,
  AlertTriangle,
  CheckCircle2,
  CalendarClock,
  X,
  ShieldAlert,
  RefreshCw,
} from "lucide-react";
import {
  createGage,
  deleteGage,
  getAlerts,
  getGages,
  getGRRHistory,
  showToast,
  type AlertItem,
  type Gage as ApiGage,
  type GRRHistoryItem,
} from "@/api/apiClient";
import { useAppStore } from "@/lib/store";
import { parseApiDate } from "@/lib/utils";

type Gage = {
  id: string;
  name: string;
  type: string;
  nominal?: number;
  tolerance?: number;
  calibrationDue?: string; // ISO yyyy-mm-dd
  createdAt: string;
};

const GAGES_KEY = "arad-gages";

const SAMPLE_GAGES: Omit<Gage, "id" | "createdAt">[] = [
  { name: "CMM-04", type: "Coordinate measuring machine", nominal: 25.0, tolerance: 0.05, calibrationDue: futureDate(45) },
  { name: "Torque Press Line 1", type: "In-line torque sensor", nominal: 5.0, tolerance: 0.1, calibrationDue: futureDate(8) },
  { name: "Caliper-11", type: "Digital caliper", nominal: 12.0, tolerance: 0.02, calibrationDue: pastDate(3) },
];

function futureDate(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
function pastDate(days: number) {
  return futureDate(-days);
}

function loadGages(): Gage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(GAGES_KEY);
    return raw ? (JSON.parse(raw) as Gage[]) : [];
  } catch {
    return [];
  }
}

function saveGages(gages: Gage[]) {
  window.localStorage.setItem(GAGES_KEY, JSON.stringify(gages));
}

/** Map a server gage record to the page's local shape. */
function fromApi(g: ApiGage): Gage {
  return {
    id: g.id,
    name: g.name,
    type: g.type,
    nominal: g.nominal ?? undefined,
    tolerance: g.tolerance ?? undefined,
    calibrationDue: g.calibration_due ?? undefined,
    createdAt: g.created_at,
  };
}

type CalStatus = { label: string; tone: "ok" | "warn" | "crit"; days: number | null };

function calibrationStatus(due?: string): CalStatus {
  if (!due) return { label: "Not scheduled", tone: "warn", days: null };
  const target = parseApiDate(due).getTime();
  if (Number.isNaN(target)) return { label: "Not scheduled", tone: "warn", days: null };
  const days = Math.ceil((target - Date.now()) / (24 * 60 * 60 * 1000));
  if (days < 0) return { label: `Overdue ${Math.abs(days)}d`, tone: "crit", days };
  if (days <= 14) return { label: `Due in ${days}d`, tone: "warn", days };
  return { label: `Due in ${days}d`, tone: "ok", days };
}

const TONE_BADGE: Record<CalStatus["tone"], string> = {
  ok: "badge-success",
  warn: "badge-warning",
  crit: "badge-critical",
};

const SEVERITY_RANK: Record<AlertItem["severity"], number> = { critical: 4, high: 3, medium: 2, low: 1 };

const VERDICT_LABEL: Record<GRRHistoryItem["verdict"], string> = { pass: "Excellent", acceptable: "Acceptable", fail: "Unacceptable" };
const VERDICT_BADGE: Record<GRRHistoryItem["verdict"], string> = { pass: "badge-success", acceptable: "badge-warning", fail: "badge-critical" };

export default function GagesPage() {
  const { setActivePage, setGrrPrefill } = useAppStore();
  const [gages, setGages] = useState<Gage[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [grrHistory, setGrrHistory] = useState<GRRHistoryItem[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState<Omit<Gage, "id" | "createdAt">>({ name: "", type: "", nominal: undefined, tolerance: undefined, calibrationDue: "" });

  useEffect(() => {
    setGages(loadGages());
  }, []);

  const refreshAlerts = useCallback(async () => {
    setAlertsLoading(true);
    // Backend may be offline; the registry still works from local data, so each
    // source is settled independently.
    const [gagesRes, alertRes, grrRes] = await Promise.allSettled([
      getGages(),
      getAlerts({ status: "active", limit: 100 }),
      getGRRHistory(),
    ]);
    if (gagesRes.status === "fulfilled") {
      const mapped = gagesRes.value.map(fromApi);
      setGages(mapped);
      try { window.localStorage.setItem(GAGES_KEY, JSON.stringify(mapped)); } catch {}
    }
    if (alertRes.status === "fulfilled") setAlerts(alertRes.value.items ?? []);
    if (grrRes.status === "fulfilled") setGrrHistory(grrRes.value ?? []);
    setAlertsLoading(false);
  }, []);

  useEffect(() => {
    void refreshAlerts();
  }, [refreshAlerts]);

  const persist = useCallback((next: Gage[]) => {
    setGages(next);
    saveGages(next);
  }, []);

  const addGage = async () => {
    const name = draft.name.trim();
    if (!name) {
      showToast("Enter a gage / equipment name.");
      return;
    }
    const type = draft.type.trim() || "Inspection gage";
    try {
      await createGage({
        name,
        type,
        nominal: draft.nominal,
        tolerance: draft.tolerance,
        calibration_due: draft.calibrationDue || null,
      });
      await refreshAlerts();
      showToast(`${name} registered.`, "success");
    } catch {
      // Offline fallback so the registration workflow still completes.
      persist([
        {
          id: `gage_${Date.now().toString(36)}`,
          name,
          type,
          nominal: draft.nominal,
          tolerance: draft.tolerance,
          calibrationDue: draft.calibrationDue || undefined,
          createdAt: new Date().toISOString(),
        },
        ...gages,
      ]);
      showToast(`${name} saved offline.`, "info");
    }
    setDraft({ name: "", type: "", nominal: undefined, tolerance: undefined, calibrationDue: "" });
    setShowForm(false);
  };

  const removeGage = async (id: string) => {
    // Server records use UUIDs; offline records are prefixed "gage_".
    if (!id.startsWith("gage_")) {
      try {
        await deleteGage(id);
        await refreshAlerts();
        return;
      } catch {
        showToast("Could not delete on the server; removed locally.", "info");
      }
    }
    persist(gages.filter((g) => g.id !== id));
  };

  const loadSamples = async () => {
    try {
      await Promise.all(
        SAMPLE_GAGES.map((g) =>
          createGage({
            name: g.name,
            type: g.type,
            nominal: g.nominal,
            tolerance: g.tolerance,
            calibration_due: g.calibrationDue ?? null,
          }),
        ),
      );
      await refreshAlerts();
      showToast("Sample gages loaded.", "success");
    } catch {
      const seeded = SAMPLE_GAGES.map((g, i) => ({
        ...g,
        id: `gage_seed_${Date.now().toString(36)}_${i}`,
        createdAt: new Date().toISOString(),
      }));
      persist([...seeded, ...gages]);
      showToast("Sample gages loaded offline.", "info");
    }
  };

  const runStudy = (gage: Gage) => {
    setGrrPrefill({ processName: gage.name, partTolerance: gage.tolerance });
    setActivePage("grr");
    showToast(`Starting GR&R study for ${gage.name}.`, "info");
  };

  // Map each gage to its open alerts (matched by process name).
  const alertsByGage = useMemo(() => {
    const map = new Map<string, AlertItem[]>();
    for (const gage of gages) {
      const key = gage.name.toLowerCase();
      const matched = alerts.filter((a) => (a.process_name || "").toLowerCase().includes(key) || key.includes((a.process_name || "").toLowerCase()));
      map.set(gage.id, matched);
    }
    return map;
  }, [gages, alerts]);

  // Match GR&R studies to gages by name (history is newest-first from the API).
  const grrByGage = useMemo(() => {
    const map = new Map<string, { latest: GRRHistoryItem | null; count: number }>();
    for (const gage of gages) {
      const key = gage.name.toLowerCase();
      const studies = grrHistory.filter((h) => (h.process_name || "").toLowerCase() === key);
      map.set(gage.id, { latest: studies[0] ?? null, count: studies.length });
    }
    return map;
  }, [gages, grrHistory]);

  const overdueCount = gages.filter((g) => calibrationStatus(g.calibrationDue).tone === "crit").length;
  const flaggedCount = gages.filter((g) => (alertsByGage.get(g.id) ?? []).length > 0).length;

  return (
    <div className="h-full overflow-y-auto px-4 py-6 md:px-6" style={{ color: "var(--text-primary)" }}>
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        {/* Header */}
        <header className="surface-card edge-glow px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-4">
              <div
                className="mt-0.5 flex h-11 w-11 items-center justify-center rounded-xl border"
                style={{
                  borderColor: "var(--accent-bg-strong)",
                  background: "var(--accent-bg)",
                  color: "var(--accent-bright)",
                  boxShadow: "0 0 24px -6px rgba(78,140,255,0.5), inset 0 1px 0 rgba(255,255,255,0.08)",
                }}
              >
                <Ruler size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="page-title md:text-[26px]">Gage Registry</h1>
                  <HelpTip text="Your list of inspection gauges and fixtures with their calibration status. From any gage you can launch a GR&R study in one click to confirm it's measuring reliably." />
                </div>
                <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                  Inspection equipment & fixtures — calibration status, open alerts, and one-click GR&R studies.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => void refreshAlerts()} className="btn-icon h-10 w-10 rounded-xl" title="Refresh alert status">
                <RefreshCw size={14} className={alertsLoading ? "animate-spin" : undefined} />
              </button>
              <button onClick={() => setShowForm((v) => !v)} className="btn btn-primary">
                <Plus size={16} /> Register Gage
              </button>
            </div>
          </div>

          {/* Stat strip */}
          <div className="mt-5 grid grid-cols-3 gap-3">
            <Stat label="Registered" value={gages.length} />
            <Stat label="Calibration overdue" value={overdueCount} tone={overdueCount ? "var(--critical-text)" : undefined} />
            <Stat label="With open alerts" value={flaggedCount} tone={flaggedCount ? "var(--critical-text)" : undefined} />
          </div>

          {/* Register form */}
          <AnimatePresence>
            {showForm && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-5 overflow-hidden"
              >
                <div className="panel-inset p-4">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <FormField label="Name / Asset ID">
                      <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className="input-field" placeholder="e.g. CMM-04" />
                    </FormField>
                    <FormField label="Type">
                      <input value={draft.type} onChange={(e) => setDraft({ ...draft, type: e.target.value })} className="input-field" placeholder="e.g. Coordinate measuring machine" />
                    </FormField>
                    <FormField label="Calibration due">
                      <input type="date" value={draft.calibrationDue} onChange={(e) => setDraft({ ...draft, calibrationDue: e.target.value })} className="input-field" />
                    </FormField>
                    <FormField label="Nominal" optional>
                      <input type="number" step="0.0001" value={draft.nominal ?? ""} onChange={(e) => setDraft({ ...draft, nominal: e.target.value === "" ? undefined : Number(e.target.value) })} className="input-field stat-number" placeholder="Optional" />
                    </FormField>
                    <FormField label="Tolerance" optional>
                      <input type="number" step="0.0001" value={draft.tolerance ?? ""} onChange={(e) => setDraft({ ...draft, tolerance: e.target.value === "" ? undefined : Number(e.target.value) })} className="input-field stat-number" placeholder="Pre-fills GR&R" />
                    </FormField>
                  </div>
                  <div className="mt-4 flex items-center gap-2">
                    <button onClick={addGage} className="btn btn-primary h-9 px-4 text-sm">
                      <Plus size={15} /> Add gage
                    </button>
                    <button onClick={() => setShowForm(false)} className="btn btn-ghost h-9 px-4 text-sm">Cancel</button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </header>

        {/* Registry */}
        {gages.length === 0 ? (
          <div className="surface-card flex min-h-[260px] flex-col items-center justify-center px-6 py-10 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border" style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)", color: "var(--text-muted)" }}>
              <Ruler size={22} />
            </div>
            <h3 className="mt-4 text-base font-semibold" style={{ color: "var(--text-primary)" }}>No gages registered</h3>
            <p className="mt-1.5 max-w-sm text-sm" style={{ color: "var(--text-muted)" }}>
              Register an inspection gage or fixture to track its calibration and run automated GR&R studies.
            </p>
            <div className="mt-5 flex items-center gap-2">
              <button onClick={() => setShowForm(true)} className="btn btn-primary"><Plus size={16} /> Register Gage</button>
              <button onClick={loadSamples} className="btn btn-secondary">Load sample gages</button>
            </div>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {gages.map((gage) => {
              const cal = calibrationStatus(gage.calibrationDue);
              const gageAlerts = alertsByGage.get(gage.id) ?? [];
              const topSeverity = gageAlerts.slice().sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity])[0]?.severity;
              return (
                <motion.div
                  key={gage.id}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="surface-card group flex flex-col p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>{gage.name}</h3>
                      <p className="mt-0.5 truncate text-xs" style={{ color: "var(--text-muted)" }}>{gage.type}</p>
                    </div>
                    <button
                      onClick={() => removeGage(gage.id)}
                      className="btn-icon h-8 w-8 shrink-0 opacity-0 transition group-hover:opacity-100"
                      title="Remove gage"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className={`badge ${TONE_BADGE[cal.tone]} h-6 gap-1 px-2`}>
                      <CalendarClock size={11} /> {cal.label}
                    </span>
                    {gageAlerts.length ? (
                      <span className="badge badge-critical h-6 gap-1 px-2">
                        <ShieldAlert size={11} /> {gageAlerts.length} open{topSeverity ? ` · ${topSeverity}` : ""}
                      </span>
                    ) : (
                      <span className="badge badge-success h-6 gap-1 px-2">
                        <CheckCircle2 size={11} /> No open alerts
                      </span>
                    )}
                  </div>

                  {(gage.nominal != null || gage.tolerance != null) && (
                    <div className="mt-4 grid grid-cols-2 gap-2">
                      <div className="panel-inset px-3 py-2">
                        <div className="section-label text-[9.5px]">Nominal</div>
                        <div className="stat-number mt-1 text-sm" style={{ color: "var(--text-primary)" }}>{gage.nominal ?? "—"}</div>
                      </div>
                      <div className="panel-inset px-3 py-2">
                        <div className="section-label text-[9.5px]">Tolerance</div>
                        <div className="stat-number mt-1 text-sm" style={{ color: "var(--text-primary)" }}>{gage.tolerance ?? "—"}</div>
                      </div>
                    </div>
                  )}

                  {gageAlerts[0] && (
                    <p className="mt-3 line-clamp-2 text-xs leading-5" style={{ color: "var(--text-secondary)" }}>
                      <AlertTriangle size={11} className="mr-1 inline" style={{ color: "var(--critical-text)" }} />
                      {gageAlerts[0].message}
                    </p>
                  )}

                  {(() => {
                    const summary = grrByGage.get(gage.id);
                    if (!summary || !summary.latest) {
                      return (
                        <div className="mt-3 panel-inset px-3 py-2 text-xs" style={{ color: "var(--text-muted)" }}>
                          No GR&R studies yet
                        </div>
                      );
                    }
                    const v = summary.latest.verdict;
                    return (
                      <div className="mt-3 flex items-center justify-between panel-inset px-3 py-2">
                        <div>
                          <div className="section-label text-[9.5px]">Latest GR&R</div>
                          <div className="stat-number mt-0.5 text-sm" style={{ color: "var(--text-primary)" }}>
                            {summary.latest.grr_percent != null ? `${summary.latest.grr_percent.toFixed(1)}%` : "—"}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <span className={`badge ${VERDICT_BADGE[v]} h-5 px-1.5 text-[9.5px]`}>{VERDICT_LABEL[v]}</span>
                          <span className="text-[10px]" style={{ color: "var(--text-ghost)" }}>
                            {summary.count} stud{summary.count === 1 ? "y" : "ies"}
                          </span>
                        </div>
                      </div>
                    );
                  })()}

                  <div className="mt-auto pt-4">
                    <button onClick={() => runStudy(gage)} className="btn btn-secondary h-9 w-full text-sm">
                      <FlaskConical size={15} /> Run GR&R study
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="panel-inset px-4 py-3">
      <div className="section-label text-[9.5px]">{label}</div>
      <div className="stat-number mt-1 text-2xl" style={{ color: tone || "var(--text-primary)" }}>{value}</div>
    </div>
  );
}

function FormField({ label, optional, children }: { label: string; optional?: boolean; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>{label}</span>
        {optional ? <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--text-ghost)" }}>Optional</span> : null}
      </div>
      {children}
    </label>
  );
}
