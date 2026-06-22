"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, Check, CheckCircle2, Loader2, PenLine, Plus, RotateCcw, Send, Wrench, X } from "lucide-react";
import HelpTip from "@/components/ui/HelpTip";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getSPCHistory,
  getSPCProcesses,
  showToast,
  submitSPCData,
  type SPCDataResponse,
  type SPCProcessSummary,
  type SPCViolation,
} from "@/api/apiClient";
import { useRealtimeStream } from "@/api/realtime";

type ChartPoint = {
  index: number;
  value: number;
  violation?: SPCViolation;
};

const STORAGE_KEY = "arad-spc-active-process";

function formatNumber(value: number | null | undefined) {
  return Number.isFinite(value) ? Number(value).toFixed(4) : "--";
}

function buildChartPoints(values: number[], violations: SPCViolation[]) {
  return values.map((value, index) => ({
    index,
    value,
    violation: violations.find((violation) => violation.index === index),
  }));
}

function SPCTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;

  return (
    <div className="elevated-card px-3.5 py-2.5 text-xs" style={{ color: "var(--text-secondary)" }}>
      <div className="stat-number text-sm" style={{ color: "var(--text-primary)" }}>
        {point.value.toFixed(4)}
      </div>
      <div className="mt-1" style={{ color: "var(--text-muted)" }}>
        Measurement {point.index + 1}
      </div>
      {point.violation ? (
        <div className="mt-2 max-w-56" style={{ color: "var(--critical-text)" }}>
          {point.violation.description}
        </div>
      ) : null}
    </div>
  );
}

type BaselineLimits = { ucl: number; lcl: number; target: number };

const BASELINE_KEY = "arad-spc-baseline";
const ACKS_KEY = "arad-spc-acks";

const violationKey = (violation: SPCViolation) => `${violation.rule}:${violation.index}`;

type RuleInfo = { title: string; action: string };

/**
 * Human-readable title + recommended corrective action for an SPC rule code.
 * Handles Nelson / Western-Electric variants (rule_1, nelson_rule_1, …) by the
 * trailing number, falling back to the backend description.
 */
function ruleInfo(rule: string, description: string): RuleInfo {
  const num = (rule.toLowerCase().match(/(\d+)/) || [])[1];
  const map: Record<string, RuleInfo> = {
    "1": { title: "Point beyond 3σ (outside control limits)", action: "Investigate immediately — a special cause is likely. Re-verify the measurement, then check machine setup, material lot, and tooling for this sample." },
    "2": { title: "9 points on one side of the centerline", action: "The process mean has shifted. Review setup changes, a new material lot, or an operator/shift change since the run began." },
    "3": { title: "6 points trending up or down", action: "Gradual drift in progress. Check for tool wear, temperature change, or a loosening fixture." },
    "4": { title: "14 points alternating up and down", action: "Likely over-adjustment (tampering) or two alternating sources — e.g. two fixtures, heads, or gauges." },
    "5": { title: "2 of 3 points in Zone A (beyond 2σ)", action: "Early instability warning. Monitor closely and look for an emerging special cause." },
    "6": { title: "4 of 5 points in Zone B (beyond 1σ)", action: "A small sustained shift. Review recent process-input changes." },
    "7": { title: "15 points hugging the centerline (Zone C)", action: "Unusually low variation — check for a measurement problem or incorrect/stratified limits." },
    "8": { title: "8 points beyond 1σ with none in Zone C", action: "Mixture pattern — the data likely comes from two distinct process streams." },
  };
  if (num && map[num]) return map[num];
  return { title: description || rule, action: "Investigate the flagged measurement for an assignable cause and document the disposition." };
}

export default function SPCPage() {
  const [processDraft, setProcessDraft] = useState("Torque Press Line 1");
  const [processName, setProcessName] = useState("");
  const [measurementDraft, setMeasurementDraft] = useState("");
  const [measurements, setMeasurements] = useState<number[]>([]);
  const [analysis, setAnalysis] = useState<SPCDataResponse | null>(null);
  const [baseline, setBaseline] = useState<BaselineLimits | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [acks, setAcks] = useState<Record<string, { acked: boolean; note: string }>>({});
  const [noteDraft, setNoteDraft] = useState("");
  const [processes, setProcesses] = useState<SPCProcessSummary[]>([]);
  const [processesLoading, setProcessesLoading] = useState(false);

  const persistBaseline = (name: string, limits: BaselineLimits | null) => {
    setBaseline(limits);
    if (limits) {
      window.localStorage.setItem(BASELINE_KEY, JSON.stringify({ process: name, ...limits }));
    } else {
      window.localStorage.removeItem(BASELINE_KEY);
    }
  };

  // Monotonic sequence so a slow earlier response can never overwrite the
  // result of a newer submission (Gemini narratives make latencies uneven).
  const analysisSeq = useRef(0);

  const loadHistory = useCallback(async () => {
    if (!processName) {
      return;
    }

    const seq = ++analysisSeq.current;
    setHistoryLoading(true);
    try {
      const history = await getSPCHistory(processName);
      const values = [...history.points]
        .reverse()
        .map((point) => Number(point.value))
        .filter(Number.isFinite)
        .slice(-50);

      if (seq !== analysisSeq.current) return;
      setMeasurements(values);
      if (values.length >= 2) {
        // Stats-only recompute: persist nothing (new_values: []).
        const result = await submitSPCData({
          process_name: processName,
          measurements: values,
          new_values: [],
          ...(baseline ? { ucl: baseline.ucl, lcl: baseline.lcl, target: baseline.target } : {}),
        });
        if (seq !== analysisSeq.current) return;
        setAnalysis(result);
      } else {
        setAnalysis(null);
      }
    } catch {
      showToast("SPC history could not be loaded.");
    } finally {
      setHistoryLoading(false);
    }
  }, [processName, baseline]);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setProcessName(stored);
      setProcessDraft(stored);
      try {
        const rawBaseline = window.localStorage.getItem(BASELINE_KEY);
        if (rawBaseline) {
          const parsed = JSON.parse(rawBaseline) as BaselineLimits & { process?: string };
          if (parsed.process === stored && Number.isFinite(parsed.ucl) && Number.isFinite(parsed.lcl)) {
            setBaseline({ ucl: parsed.ucl, lcl: parsed.lcl, target: parsed.target });
          }
        }
      } catch {
        // Ignore corrupted baseline cache.
      }
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const loadProcesses = useCallback(async () => {
    setProcessesLoading(true);
    try {
      const res = await getSPCProcesses();
      setProcesses(res.processes ?? []);
    } catch {
      /* backend unreachable — leave the list empty */
    } finally {
      setProcessesLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProcesses();
  }, [loadProcesses]);

  // Load per-process acknowledgements / disposition notes (client-side QA log).
  useEffect(() => {
    setSelectedKey(null);
    if (!processName) {
      setAcks({});
      return;
    }
    try {
      const raw = window.localStorage.getItem(`${ACKS_KEY}:${processName}`);
      setAcks(raw ? (JSON.parse(raw) as Record<string, { acked: boolean; note: string }>) : {});
    } catch {
      setAcks({});
    }
  }, [processName]);

  useRealtimeStream({
    enabled: Boolean(processName),
    onEvent: (event) => {
      const eventType = String(event.type || "");
      if (!processName) {
        return;
      }

      // poll.tick is intentionally ignored here: reloading history mid-entry
      // would replace the operator's in-progress measurement window.
      const eventProcess = String(event.process_name || event.characteristic_name || event.equipment_id || "");
      if (!eventProcess) {
        return;
      }

      if (["measurement.processed", "spc.analysis", "mes.event", "qms.event"].includes(eventType) && eventProcess === processName) {
        void loadHistory();
      }
    },
  });

  const chartPoints = useMemo(
    () => buildChartPoints(measurements, analysis?.violations ?? []),
    [measurements, analysis?.violations],
  );

  const sigma = analysis ? (analysis.ucl - analysis.lcl) / 6 : 0;
  const centerLine = analysis ? (analysis.ucl + analysis.lcl) / 2 : 0;
  const zoneOneUpper = centerLine + sigma;
  const zoneOneLower = centerLine - sigma;
  const zoneTwoUpper = centerLine + 2 * sigma;
  const zoneTwoLower = centerLine - 2 * sigma;
  const activeViolations = analysis?.violations ?? [];
  const selectedViolation = activeViolations.find((violation) => violationKey(violation) === selectedKey) ?? null;

  const selectViolation = (violation: SPCViolation) => {
    const key = violationKey(violation);
    setSelectedKey(key);
    setNoteDraft(acks[key]?.note ?? "");
  };

  const updateAck = (key: string, patch: Partial<{ acked: boolean; note: string }>) => {
    setAcks((prev) => {
      const base = prev[key] ?? { acked: false, note: "" };
      const next = { ...prev, [key]: { ...base, ...patch } };
      if (processName) window.localStorage.setItem(`${ACKS_KEY}:${processName}`, JSON.stringify(next));
      return next;
    });
  };

  const registerProcess = (nameArg?: string) => {
    const name = (nameArg ?? processDraft).trim();
    if (!name) {
      showToast("Enter a process name.");
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, name);
    setProcessDraft(name);
    setProcessName(name);
    setMeasurements([]);
    setAnalysis(null);
    persistBaseline(name, null);
    showToast(`${name} added to SPC monitor.`);
  };

  const submitMeasurement = async () => {
    if (!processName) {
      showToast("Add a process before submitting measurements.");
      return;
    }

    const value = Number(measurementDraft);
    if (!Number.isFinite(value)) {
      showToast("Enter a valid numeric measurement.");
      return;
    }

    const nextMeasurements = [...measurements, value].slice(-50);
    setMeasurements(nextMeasurements);
    setMeasurementDraft("");

    if (nextMeasurements.length < 2) {
      showToast("Add one more point to calculate limits.");
      return;
    }

    setLoading(true);
    const seq = ++analysisSeq.current;
    try {
      const result = await submitSPCData({
        process_name: processName,
        measurements: nextMeasurements,
        new_values: [value],
        // Judge new points against frozen baseline limits (Phase II SPC);
        // without this, drifting data inflates its own control limits.
        ...(baseline ? { ucl: baseline.ucl, lcl: baseline.lcl, target: baseline.target } : {}),
      });
      if (seq !== analysisSeq.current) return;
      setAnalysis(result);
      if (!baseline && nextMeasurements.length >= 15) {
        persistBaseline(processName, { ucl: result.ucl, lcl: result.lcl, target: result.mean });
        showToast("Control limits frozen from baseline. New points are judged against them.");
      }
      if (result.violations.length) {
        showToast(`${result.violations.length} SPC violation${result.violations.length === 1 ? "" : "s"} detected.`);
      }
    } catch {
      showToast("SPC analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const loadSampleSet = async () => {
    const sample = [
      5.01, 4.99, 5.02, 5.0, 5.03, 4.98, 5.01, 5.02, 4.99, 5.0, 5.01, 5.03, 4.98, 5.02, 5.0,
    ];
    setMeasurements(sample);
    if (!processName) {
      showToast("Add a process before loading sample data.");
      return;
    }

    setLoading(true);
    try {
      const result = await submitSPCData({ process_name: processName, measurements: sample, new_values: sample });
      setAnalysis(result);
      persistBaseline(processName, { ucl: result.ucl, lcl: result.lcl, target: result.mean });
      showToast("Baseline established — control limits frozen for live monitoring.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto px-6 py-7 md:px-10 lg:py-9" style={{ color: "var(--text-primary)" }}>
      <div className="mx-auto flex max-w-[1500px] flex-col gap-7">
        <header className="surface-card px-7 py-7 lg:px-9 lg:py-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-4">
              <div
                className="mt-0.5 flex h-12 w-12 items-center justify-center rounded-2xl border"
                style={{ borderColor: "rgba(34,211,238,0.3)", background: "var(--live-bg)", color: "var(--live)", boxShadow: "0 0 28px -6px rgba(34,211,238,0.5), inset 0 1px 0 rgba(255,255,255,0.1)" }}
              >
                <Activity size={22} />
              </div>
              <div>
                <div className="kicker mb-2" style={{ color: "var(--live)" }}>
                  <span className="live-dot" style={{ width: 6, height: 6, background: "var(--live)" }} />
                  Real-Time Telemetry
                </div>
                <div className="flex items-center gap-2">
                  <h1 className="text-display gradient-text text-[26px] font-semibold md:text-[33px]">SPC Control Monitor</h1>
                  <HelpTip text="SPC = Statistical Process Control: live control charts. The app applies standard rules (like the Nelson rules) and automatically flags points that look out of control, so you don't have to watch every measurement yourself." />
                </div>
                <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                  Live statistical process control — Nelson rules, control limits, and violation detection.
                </p>
              </div>
            </div>
            <div className="glass-strong rounded-2xl px-5 py-3.5">
              <div className="section-label text-[10px]">Active Process</div>
              <div className="mt-1.5 flex items-center gap-2.5 text-sm font-semibold" style={{ color: "var(--success-text)" }}>
                <span className="live-dot" style={{ width: 7, height: 7 }} />
                {processName || "No process added"}
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-6 xl:grid-cols-[360px_1fr]">
          <div className="space-y-4">
            <div className="surface-card p-5">
              <div className="flex items-center justify-between">
                <h2 className="section-label">Monitored Processes</h2>
                <button onClick={() => void loadProcesses()} className="btn-icon h-7 w-7" title="Refresh list">
                  <RotateCcw size={13} />
                </button>
              </div>
              <p className="mt-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
                Live series the monitor is tracking. Click one to chart its real data.
              </p>
              {processesLoading ? (
                <div className="mt-3 flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  <Loader2 size={13} className="animate-spin" /> Loading…
                </div>
              ) : processes.length === 0 ? (
                <p className="mt-3 text-xs" style={{ color: "var(--text-ghost)" }}>
                  No data yet. Upload measurements on the Connections page, or add a process below to chart it by hand.
                </p>
              ) : (
                <div className="mt-3 space-y-1.5">
                  {processes.map((proc) => {
                    const active = proc.name === processName;
                    return (
                      <button
                        key={proc.name}
                        onClick={() => registerProcess(proc.name)}
                        className="flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-colors hover:border-[var(--border-accent)]"
                        style={{
                          borderColor: active ? "var(--border-accent)" : "var(--border-default)",
                          background: active ? "var(--accent-bg)" : "var(--bg-primary)",
                        }}
                      >
                        <span className="truncate text-sm font-medium" style={{ color: active ? "var(--accent-bright)" : "var(--text-primary)" }}>
                          {proc.name}
                        </span>
                        <span className="shrink-0 font-mono text-[10px]" style={{ color: "var(--text-muted)" }}>
                          {proc.points} pts
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="surface-card p-5">
              <h2 className="section-label">Add Process</h2>
              <div className="mt-4 flex gap-2">
                <input
                  value={processDraft}
                  onChange={(event) => setProcessDraft(event.target.value)}
                  className="input-field"
                  placeholder="Torque Press Line 1"
                />
                <button
                  onClick={() => registerProcess()}
                  className="btn btn-primary h-[38px] w-[38px] shrink-0 !px-0"
                  title="Add process"
                >
                  <Plus size={17} />
                </button>
              </div>
            </div>

            <div className="surface-card p-5">
              <h2 className="section-label">Submit Measurement</h2>
              <div className="mt-4 flex gap-2">
                <input
                  value={measurementDraft}
                  onChange={(event) => setMeasurementDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void submitMeasurement();
                  }}
                  type="number"
                  step="0.0001"
                  className="input-field stat-number"
                  placeholder="5.0120"
                />
                <button
                  onClick={() => void submitMeasurement()}
                  disabled={loading}
                  className="btn btn-secondary h-[38px] w-[38px] shrink-0 !px-0"
                  style={{ color: "var(--live)" }}
                  title="Submit measurement"
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={15} />}
                </button>
              </div>
              <button onClick={() => void loadSampleSet()} className="btn btn-ghost mt-3 h-8 gap-2 px-2.5 text-xs">
                <RotateCcw size={13} /> Load 15 baseline points
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Metric label="Points" value={measurements.length} />
              <Metric label="Mean" value={formatNumber(analysis?.mean)} />
              <Metric label="UCL" value={formatNumber(analysis?.ucl)} tone="var(--critical-text)" />
              <Metric label="LCL" value={formatNumber(analysis?.lcl)} tone="var(--critical-text)" />
            </div>
          </div>

          <div className="surface-card p-5">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="section-label">Control Chart</h2>
                <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                  {historyLoading ? "Loading persisted history…" : `${chartPoints.length} measurements in the active window`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {baseline && (
                  <span className="badge badge-info h-7 gap-1.5 px-3" title={`Frozen limits — UCL ${baseline.ucl.toFixed(4)} · LCL ${baseline.lcl.toFixed(4)}`}>
                    Baseline locked
                  </span>
                )}
                {activeViolations.length ? (
                  <span className="badge badge-critical h-7 gap-1.5 px-3">
                    <AlertTriangle size={12} /> {activeViolations.length} violation{activeViolations.length === 1 ? "" : "s"}
                  </span>
                ) : (
                  <span className="badge badge-success h-7 gap-1.5 px-3">
                    <CheckCircle2 size={12} /> In control
                  </span>
                )}
              </div>
            </div>

            <div className="panel-inset mt-5 h-[430px] p-4">
              {chartPoints.length >= 2 && analysis ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartPoints} margin={{ top: 15, right: 24, left: 0, bottom: 8 }}>
                    <defs>
                      <linearGradient id="spcLine" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.65} />
                        <stop offset="100%" stopColor="#22d3ee" stopOpacity={1} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
                    <ReferenceArea y1={zoneOneUpper} y2={zoneOneLower} fill="rgba(16,185,129,0.045)" />
                    <ReferenceArea y1={zoneTwoUpper} y2={zoneOneUpper} fill="rgba(245,158,11,0.04)" />
                    <ReferenceArea y1={zoneOneLower} y2={zoneTwoLower} fill="rgba(245,158,11,0.04)" />
                    <ReferenceLine y={analysis.ucl} stroke="var(--critical)" strokeDasharray="8 4" label={{ value: "UCL", position: "right", fill: "var(--critical-text)", fontSize: 10 }} />
                    <ReferenceLine y={centerLine} stroke="var(--live)" strokeDasharray="4 4" label={{ value: "CL", position: "right", fill: "var(--live)", fontSize: 10 }} />
                    <ReferenceLine y={analysis.lcl} stroke="var(--critical)" strokeDasharray="8 4" label={{ value: "LCL", position: "right", fill: "var(--critical-text)", fontSize: 10 }} />
                    <XAxis dataKey="index" tickFormatter={(value) => String(Number(value) + 1)} tick={{ fill: "var(--text-muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "var(--text-muted)", fontSize: 10 }} width={62} tickFormatter={(value) => Number(value).toFixed(3)} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                    <Tooltip content={<SPCTooltip />} />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="url(#spcLine)"
                      strokeWidth={2.5}
                      isAnimationActive
                      animationDuration={1100}
                      animationEasing="ease-out"
                      style={{ filter: "drop-shadow(0 0 6px rgba(34,211,238,0.45))" }}
                      dot={(props) => {
                        if (typeof props.cx !== "number" || typeof props.cy !== "number") return null;
                        const point = props.payload as ChartPoint;
                        const key = point.violation ? violationKey(point.violation) : null;
                        const isSelected = key !== null && key === selectedKey;
                        const isAcked = key !== null && Boolean(acks[key]?.acked);
                        return (
                          <circle
                            key={props.index}
                            cx={props.cx}
                            cy={props.cy}
                            r={point.violation ? (isSelected ? 6.5 : 5) : 3}
                            fill={point.violation ? (isAcked ? "#f59e0b" : "var(--critical)") : "var(--live)"}
                            stroke={isSelected ? "var(--text-primary)" : "var(--bg-root)"}
                            strokeWidth={isSelected ? 2.5 : 2}
                            style={{ cursor: point.violation ? "pointer" : "default" }}
                            onClick={() => point.violation && selectViolation(point.violation)}
                          />
                        );
                      }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-center">
                  <div>
                    <div
                      className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border"
                      style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)", color: "var(--text-muted)" }}
                    >
                      <Activity size={18} />
                    </div>
                    <p className="mt-4 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      Waiting for measurements
                    </p>
                    <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                      Submit at least two values to render control limits.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {activeViolations.length ? (
              <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
                <div className="space-y-2">
                  <div className="section-label text-[10px]">Violations · click to investigate</div>
                  {activeViolations.map((violation, index) => {
                    const key = violationKey(violation);
                    const selected = key === selectedKey;
                    const acked = Boolean(acks[key]?.acked);
                    const info = ruleInfo(violation.rule, violation.description);
                    return (
                      <button
                        key={`${key}-${index}`}
                        onClick={() => selectViolation(violation)}
                        className="w-full rounded-xl border px-4 py-3 text-left text-sm transition"
                        style={{
                          borderColor: selected ? "var(--critical)" : "rgba(239,68,68,0.22)",
                          background: selected ? "rgba(239,68,68,0.12)" : "var(--critical-bg)",
                          color: "var(--text-primary)",
                          boxShadow: `inset 2.5px 0 0 ${selected ? "var(--critical)" : "rgba(239,68,68,0.4)"}`,
                        }}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold leading-snug" style={{ color: "var(--critical-text)" }}>
                            {info.title}
                          </span>
                          {acked ? (
                            <span className="badge badge-success h-5 shrink-0 gap-1 px-1.5 text-[10px]">
                              <Check size={10} /> Ack
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-1 font-mono text-[10px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                          Measurement {violation.index + 1} · {violation.rule}
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="panel-inset p-4">
                  {selectedViolation ? (
                    (() => {
                      const info = ruleInfo(selectedViolation.rule, selectedViolation.description);
                      const key = violationKey(selectedViolation);
                      const ack = acks[key];
                      return (
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="font-mono text-[10px] uppercase tracking-wider" style={{ color: "var(--critical-text)" }}>
                                {selectedViolation.rule}
                              </div>
                              <h3 className="mt-1 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                                {info.title}
                              </h3>
                            </div>
                            <button onClick={() => setSelectedKey(null)} className="btn-icon" aria-label="Close detail">
                              <X size={15} />
                            </button>
                          </div>

                          <div className="mt-3 grid grid-cols-2 gap-2">
                            <div className="surface-card p-3">
                              <div className="section-label text-[10px]">Measurement #</div>
                              <div className="stat-number mt-1.5 text-lg" style={{ color: "var(--text-primary)" }}>
                                {selectedViolation.index + 1}
                              </div>
                            </div>
                            <div className="surface-card p-3">
                              <div className="section-label text-[10px]">Value</div>
                              <div className="stat-number mt-1.5 text-lg" style={{ color: "var(--critical-text)" }}>
                                {formatNumber(measurements[selectedViolation.index])}
                              </div>
                            </div>
                          </div>

                          <div className="mt-3 rounded-lg border px-3 py-2.5" style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)" }}>
                            <div className="section-label flex items-center gap-1.5 text-[10px]">
                              <Wrench size={12} /> Recommended action
                            </div>
                            <p className="mt-1.5 text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
                              {info.action}
                            </p>
                          </div>

                          {selectedViolation.description ? (
                            <p className="mt-2 text-[11px]" style={{ color: "var(--text-muted)" }}>
                              Detector: {selectedViolation.description}
                            </p>
                          ) : null}

                          <label className="mt-3 block">
                            <span className="section-label flex items-center gap-1.5 text-[10px]">
                              <PenLine size={12} /> Annotation
                            </span>
                            <textarea
                              value={noteDraft}
                              onChange={(event) => setNoteDraft(event.target.value)}
                              rows={2}
                              placeholder="Add a disposition note…"
                              className="input-field mt-1.5 text-xs"
                            />
                          </label>

                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <button
                              onClick={() => updateAck(key, { acked: !ack?.acked })}
                              className={`btn h-8 px-3 text-xs ${ack?.acked ? "btn-secondary" : "btn-primary"}`}
                            >
                              {ack?.acked ? <><RotateCcw size={13} /> Un-acknowledge</> : <><Check size={13} /> Acknowledge</>}
                            </button>
                            <button
                              onClick={() => { updateAck(key, { note: noteDraft }); showToast("Annotation saved."); }}
                              className="btn btn-secondary h-8 px-3 text-xs"
                            >
                              <PenLine size={13} /> Save note
                            </button>
                          </div>

                          {ack?.acked ? (
                            <div className="mt-2 text-[11px]" style={{ color: "var(--success-text)" }}>
                              Acknowledged{ack?.note ? " · note on file" : ""}.
                            </div>
                          ) : null}
                        </div>
                      );
                    })()
                  ) : (
                    <div className="flex h-full min-h-[160px] flex-col items-center justify-center text-center">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl border" style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)", color: "var(--text-muted)" }}>
                        <AlertTriangle size={16} />
                      </div>
                      <p className="mt-3 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                        Investigate a violation
                      </p>
                      <p className="mt-1 max-w-[220px] text-xs" style={{ color: "var(--text-muted)" }}>
                        Click any red point on the chart or a violation in the list to see the rule and recommended action.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="surface-card p-4">
      <div className="section-label text-[10px]">{label}</div>
      <div className="stat-number mt-2 text-xl" style={{ color: tone || "var(--text-primary)" }}>
        {value}
      </div>
    </div>
  );
}
