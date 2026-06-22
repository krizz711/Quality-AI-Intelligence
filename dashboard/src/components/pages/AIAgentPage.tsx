"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  DollarSign,
  Send,
  ShieldCheck,
  Bot,
  Play,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Brain,
  LayoutGrid,
} from "lucide-react";

// ── types ────────────────────────────────────────────────────────────────────
interface Step { agent: string; title: string; detail: string; status: string }
interface ScanResult {
  process: string;
  in_control: boolean;
  data_source?: string;
  series: number[];
  control_limits: { ucl: number; center_line: number; lcl: number; sigma: number };
  violations: { index: number; value: number; rule: string; description: string }[];
  violation_count: number;
  summary?: string;
  copq?: { total_copq: number; savings_from_early_detection: number; annualized_copq: number; cost_if_caught_late: number };
  steps: Step[];
  alert: { title: string; message: string; severity: string } | null;
}
interface FleetRow { process: string; in_control: boolean; violation_count: number; copq_total: number }
interface FleetResult { source: string; processes: FleetRow[]; at_risk: number; total_exposure: number }

const AGENT_ICON: Record<string, React.ComponentType<{ size?: number; className?: string; style?: React.CSSProperties }>> = {
  process_monitor: Activity, business_analyst: DollarSign, action_dispatch: Send, measurement_analyst: ShieldCheck,
};
const AGENTS = [
  { id: "process_monitor", label: "Process Monitor", desc: "SPC + Nelson rules" },
  { id: "business_analyst", label: "Business Analyst", desc: "Cost of Poor Quality" },
  { id: "action_dispatch", label: "Action Dispatch", desc: "Slack + JIRA (approval)" },
];

function SpcMiniChart({ scan }: { scan: ScanResult }) {
  const W = 640, H = 200, pad = 28;
  const { series, control_limits: cl, violations } = scan;
  const viol = new Set(violations.map((v) => v.index));
  const lo = Math.min(cl.lcl, ...series) - cl.sigma;
  const hi = Math.max(cl.ucl, ...series) + cl.sigma;
  const x = (i: number) => pad + (i / (series.length - 1)) * (W - 2 * pad);
  const y = (v: number) => H - pad - ((v - lo) / (hi - lo)) * (H - 2 * pad);
  const line = series.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 220 }}>
      {[["ucl", cl.ucl, "#ef4444"], ["cl", cl.center_line, "#22c55e"], ["lcl", cl.lcl, "#ef4444"]].map(([k, val, c]) => (
        <line key={k as string} x1={pad} x2={W - pad} y1={y(val as number)} y2={y(val as number)}
          stroke={c as string} strokeWidth={1} strokeDasharray={k === "cl" ? "" : "4 4"} opacity={0.7} />
      ))}
      <path d={line} fill="none" stroke="#4e8cff" strokeWidth={1.6} />
      {series.map((v, i) => (
        <circle key={i} cx={x(i)} cy={y(v)} r={viol.has(i) ? 4.5 : 2.4}
          fill={viol.has(i) ? "#ef4444" : "#4e8cff"} stroke={viol.has(i) ? "#fff" : "none"} strokeWidth={0.8} />
      ))}
    </svg>
  );
}

export default function AIAgentPage() {
  const [processes, setProcesses] = useState<{ name: string }[]>([]);
  const [selected, setSelected] = useState("");
  const [dataSource, setDataSource] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [revealed, setRevealed] = useState(0);
  const [rootCause, setRootCause] = useState<string | null>(null);
  const [rcLoading, setRcLoading] = useState(false);
  const [fleet, setFleet] = useState<FleetResult | null>(null);
  const [fleetLoading, setFleetLoading] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<string | null>(null);
  const [chat, setChat] = useState<{ role: string; text: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    fetch("/api/agent/processes").then((r) => r.json()).then((d) => {
      setProcesses(d.processes || []); setDataSource(d.source || "");
    }).catch(() => {});
    return () => timers.current.forEach(clearTimeout);
  }, []);

  async function runScan(processName?: string) {
    const proc = processName ?? selected;
    if (processName !== undefined) setSelected(processName);
    setScanning(true); setScan(null); setRevealed(0); setDispatchResult(null); setRootCause(null);
    timers.current.forEach(clearTimeout); timers.current = [];
    try {
      const q = proc ? `?process=${encodeURIComponent(proc)}` : "";
      const data: ScanResult = await (await fetch(`/api/agent/scan${q}`, { method: "POST" })).json();
      setScan(data); setDataSource(data.data_source || "");
      data.steps.forEach((_, i) => timers.current.push(setTimeout(() => setRevealed(i + 1), 650 * (i + 1))));
      if (!data.in_control) {
        setRcLoading(true);
        fetch("/api/agent/analyze", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ process: data.process, summary: data.summary || "",
            total_copq: data.copq?.total_copq || 0, savings: data.copq?.savings_from_early_detection || 0 }),
        }).then((r) => r.json()).then((r) => setRootCause(r.analysis || null))
          .catch(() => setRootCause(null)).finally(() => setRcLoading(false));
      }
    } catch { setScan(null); } finally { setScanning(false); }
  }

  async function runFleet() {
    setFleetLoading(true);
    try { setFleet(await (await fetch("/api/agent/fleet", { method: "POST" })).json()); }
    catch { setFleet(null); } finally { setFleetLoading(false); }
  }

  async function approveAndSend() {
    if (!scan?.alert) return;
    setDispatching(true);
    try {
      const r = await (await fetch("/api/agent/dispatch", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(scan.alert),
      })).json();
      const sent = (r.sent_to || []) as string[];
      const jira = r.results?.jira?.key ? ` (JIRA ${r.results.jira.key})` : "";
      setDispatchResult(sent.length ? `Sent to ${sent.join(", ")}${jira}` : `Returned: ${r.status || "no channels"}`);
    } catch { setDispatchResult("Dispatch failed — is the agent service running?"); }
    finally { setDispatching(false); }
  }

  async function sendChat() {
    const msg = chatInput.trim();
    if (!msg || chatLoading) return;
    setChat((c) => [...c, { role: "user", text: msg }]); setChatInput(""); setChatLoading(true);
    try {
      const r = await (await fetch("/api/agent/chat", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: msg }),
      })).json();
      setChat((c) => [...c, { role: "agent", text: r.response || "(no response)" }]);
    } catch { setChat((c) => [...c, { role: "agent", text: "(agent unreachable)" }]); }
    finally { setChatLoading(false); }
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-7 md:px-10" style={{ color: "var(--text-primary)" }}>
    <div className="mx-auto max-w-[1500px] space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl" style={{ background: "var(--gradient-accent)" }}>
            <Bot size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">AI Agent</h1>
            <p className="text-sm text-[var(--text-muted)]">Autonomous multi-agent quality engineer — detect · cost · explain · notify</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={selected} onChange={(e) => setSelected(e.target.value)} className="input-field h-9 text-sm">
            <option value="">Auto (latest process)</option>
            {processes.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
          <button onClick={() => runScan()} disabled={scanning} className="btn btn-primary">
            {scanning ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />} Run Autonomous Scan
          </button>
          <button onClick={runFleet} disabled={fleetLoading} className="btn btn-secondary">
            {fleetLoading ? <Loader2 size={16} className="animate-spin" /> : <LayoutGrid size={16} />} Scan All
          </button>
        </div>
      </div>

      {/* Fleet view */}
      <AnimatePresence>
        {fleet && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface-card p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="section-label">Fleet scan — {fleet.processes.length} processes</h2>
              <div className="flex items-center gap-2">
                <span className="badge badge-critical">{fleet.at_risk} at risk</span>
                <span className="badge">${fleet.total_exposure.toLocaleString()} exposure</span>
              </div>
            </div>
            <div className="space-y-1.5">
              {fleet.processes.map((r, i) => (
                <button key={r.process} onClick={() => runScan(r.process)}
                  className="flex w-full items-center justify-between gap-3 panel-inset px-4 py-2.5 text-left transition hover:ring-1 hover:ring-[var(--accent-bright)]">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-[var(--text-muted)]">#{i + 1}</span>
                    <span className="font-medium text-[var(--text-primary)]">{r.process}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {r.copq_total > 0 && <span className="text-sm text-rose-300">${r.copq_total.toLocaleString()}</span>}
                    <span className={`badge ${r.in_control ? "badge-success" : "badge-critical"}`}>
                      {r.in_control ? "In control" : `${r.violation_count} violations`}
                    </span>
                  </div>
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs text-[var(--text-muted)]">Click any process to run a full autonomous scan on it.</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Agent roster */}
      <div className="grid gap-3 sm:grid-cols-3">
        {AGENTS.map((a) => {
          const Icon = AGENT_ICON[a.id] || Sparkles;
          const active = scan && revealed > 0 && scan.steps.slice(0, revealed).some((s) => s.agent === a.id);
          return (
            <div key={a.id} className={`surface-card p-4 transition ${active ? "ring-1 ring-[var(--accent-bright)]" : ""}`}>
              <div className="flex items-center gap-2">
                <Icon size={16} className={active ? "text-[var(--accent-bright)]" : "text-[var(--text-muted)]"} />
                <span className="font-semibold text-[var(--text-primary)]">{a.label}</span>
              </div>
              <p className="mt-1 text-xs text-[var(--text-muted)]">{a.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Scan output */}
      <AnimatePresence>
        {scan && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
            <div className="surface-card p-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="section-label">Live SPC scan — {scan.process}</h2>
                <div className="flex items-center gap-2">
                  <span className="badge" title="Where the agent read its data">
                    {scan.data_source === "live backend" ? "🟢 Live data" : "Sample data"}
                  </span>
                  <span className={`badge ${scan.in_control ? "badge-success" : "badge-critical"}`}>
                    {scan.in_control ? "In control" : `${scan.violation_count} violations`}
                  </span>
                </div>
              </div>
              <SpcMiniChart scan={scan} />
            </div>

            {/* Agent steps */}
            <div className="space-y-2.5">
              {scan.steps.slice(0, revealed).map((s, i) => {
                const Icon = AGENT_ICON[s.agent] || Sparkles;
                const tone = s.status === "alert" ? "#ef4444" : s.status === "pending" ? "#eab308" : "#22c55e";
                return (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="flex items-start gap-3 panel-inset p-3.5">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg" style={{ background: `${tone}22` }}>
                      <Icon size={15} style={{ color: tone }} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">{s.agent}</span>
                        <span className="font-semibold text-[var(--text-primary)]">{s.title}</span>
                      </div>
                      <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{s.detail}</p>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* COPQ */}
            {scan.copq && revealed >= 3 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid gap-3 sm:grid-cols-3">
                {[
                  { label: "Cost this event", value: `$${scan.copq.total_copq.toLocaleString()}`, tone: "text-rose-300" },
                  { label: "Saved by early detection", value: `$${scan.copq.savings_from_early_detection.toLocaleString()}`, tone: "text-emerald-300" },
                  { label: "Annualized exposure", value: `$${scan.copq.annualized_copq.toLocaleString()}`, tone: "text-amber-300" },
                ].map((m) => (
                  <div key={m.label} className="panel-inset p-4">
                    <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">{m.label}</div>
                    <div className={`stat-number mt-1 text-2xl ${m.tone}`}>{m.value}</div>
                  </div>
                ))}
              </motion.div>
            )}

            {/* Root cause (real LLM reasoning) */}
            {!scan.in_control && revealed >= 3 && (rcLoading || rootCause) && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface-card p-5">
                <div className="flex items-center gap-2">
                  <Brain size={16} className="text-[var(--accent-bright)]" />
                  <h3 className="section-label">Root-cause analysis — generated by the agent</h3>
                </div>
                {rcLoading ? (
                  <div className="mt-3 flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <Loader2 size={14} className="animate-spin" /> agent reasoning over the SPC pattern…
                  </div>
                ) : (
                  <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{rootCause}</p>
                )}
              </motion.div>
            )}

            {/* Drafted alert + HITL */}
            {scan.alert && revealed >= 4 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface-card p-5" style={{ borderColor: "var(--border-strong)" }}>
                <div className="flex items-center gap-2">
                  <AlertTriangle size={16} className="text-amber-400" />
                  <h3 className="section-label">Drafted alert — human approval required</h3>
                </div>
                <div className="mt-3 panel-inset p-4">
                  <div className="font-semibold text-[var(--text-primary)]">{scan.alert.title}</div>
                  <p className="mt-1.5 text-sm leading-6 text-[var(--text-secondary)]">{scan.alert.message}</p>
                </div>
                <div className="mt-4 flex items-center gap-3">
                  {!dispatchResult ? (
                    <button onClick={approveAndSend} disabled={dispatching} className="btn btn-primary">
                      {dispatching ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Approve &amp; Send to Slack + JIRA
                    </button>
                  ) : (
                    <div className="flex items-center gap-2 text-sm font-medium text-emerald-300"><CheckCircle2 size={16} /> {dispatchResult}</div>
                  )}
                  <span className="text-xs text-[var(--text-muted)]">Nothing was sent until you approved.</span>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat */}
      <div className="surface-card p-5">
        <h2 className="section-label mb-3">Ask the agent</h2>
        <div className="space-y-2.5">
          {chat.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] whitespace-pre-line rounded-2xl px-4 py-2.5 text-sm ${m.role === "user" ? "bg-[var(--accent-bright)] text-white" : "panel-inset text-[var(--text-secondary)]"}`}>{m.text}</div>
            </div>
          ))}
          {chatLoading && <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]"><Loader2 size={14} className="animate-spin" /> agent thinking…</div>}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <input value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendChat()}
            placeholder="e.g. A line drifted out of control for 30 min — what did it cost us?" className="input-field flex-1" />
          <button onClick={sendChat} disabled={chatLoading} className="btn btn-secondary"><Send size={15} /> Send</button>
        </div>
      </div>
    </div>
    </div>
  );
}
