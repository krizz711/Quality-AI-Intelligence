"use client";

import { useState, useRef, useEffect, useCallback, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  ArrowUp,
  ArrowUpRight,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { exampleChat, type ChatMessage } from "@/lib/mock-data";
import { apiClient, streamChat, showToast, type AgentStreamEvent } from "@/api/apiClient";
import { useAppStore } from "@/lib/store";
import { AgentCore } from "@/components/agent/AgentCore";
import {
  STEP_GLYPHS,
  GlyphCheck,
  GlyphSource,
  GlyphGauge,
  GlyphControlChart,
  GlyphReason,
  GlyphCompose,
} from "@/components/agent/agent-icons";

const ALLOW_MOCK =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_ALLOW_MOCK_DATA === "true") || false;

// ── Agent reasoning trace ────────────────────────────────────────────────────

type StepStatus = "pending" | "active" | "done" | "skipped";

interface TraceStep {
  id: keyof typeof STEP_GLYPHS;
  label: string; // resting label
  active: string; // gerund shown while running
  detail: string;
  source?: string; // maps to the backend's context_used keys
  status: StepStatus;
  startedAt?: number; // perf clock when the step went active (drives the live timer)
  result?: string;
  ms?: number;
}

interface AgentTrace {
  steps: TraceStep[];
  durationMs: number;
  sources: string[];
}

type AgentMessage = ChatMessage & { trace?: AgentTrace; isError?: boolean };

// The honest pipeline the /chat endpoint actually runs: it snapshots live
// context (GR&R studies → open violations → pending reviews) then reasons with
// Gemini. These steps mirror that — no invented work.
const makeSteps = (): TraceStep[] => [
  { id: "parse", label: "Parse request", active: "Interpreting request", detail: "Intent & entities", status: "pending" },
  { id: "grr", label: "GR&R studies", active: "Querying GR&R studies", detail: "Measurement-system capability", source: "recent_grr_studies", status: "pending" },
  { id: "spc", label: "Open violations", active: "Scanning SPC violations", detail: "Control-chart breaches", source: "open_violations", status: "pending" },
  { id: "review", label: "Review queue", active: "Checking pending reviews", detail: "Awaiting sign-off", source: "pending_reviews", status: "pending" },
  { id: "reason", label: "Reasoning", active: "Reasoning over context", detail: "Gemini synthesis", status: "pending" },
  { id: "compose", label: "Compose answer", active: "Composing answer", detail: "Drafting response", status: "pending" },
];

const SOURCE_LABEL: Record<string, string> = {
  recent_grr_studies: "GR&R studies",
  open_violations: "Open violations",
  pending_reviews: "Review queue",
  context_override: "Test context",
};

const SUGGESTIONS = [
  { q: "Which equipment had the worst GR&R this week?", g: GlyphGauge },
  { q: "Why is CMM-001 showing control violations?", g: GlyphControlChart },
  { q: "Summarize all critical alerts from the last 24 hours", g: GlyphControlChart },
  { q: "What's the current Cpk for bore diameter on P-2847?", g: GlyphGauge },
  { q: "Recommend corrective actions for VMM-003", g: GlyphReason },
  { q: "Draft a shift summary for the quality team", g: GlyphCompose },
];

// ── Rich text rendering ──────────────────────────────────────────────────────

function renderInline(text: string, keyBase: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
    const key = `${keyBase}-${i}`;
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={key} style={{ color: "var(--text-primary)", fontWeight: 600 }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={key}
          className="rounded px-1.5 py-0.5 font-mono text-[12px]"
          style={{ background: "var(--bg-primary)", color: "var(--accent-bright)", border: "1px solid var(--border-subtle)" }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part ? <span key={key}>{part}</span> : null;
  });
}

function MarkdownText({ content }: { content: string }) {
  const lines = content.split("\n");
  const blocks: ReactNode[] = [];
  let list: { type: "ul" | "ol"; items: string[] } | null = null;

  const flush = (key: string) => {
    if (!list) return;
    const current = list;
    blocks.push(
      <ul key={key} className="my-1 space-y-1.5">
        {current.items.map((item, i) => (
          <li key={i} className="flex gap-2.5">
            <span
              className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ background: current.type === "ol" ? "var(--accent)" : "var(--text-ghost)" }}
            />
            <span className="min-w-0">
              {current.type === "ol" && (
                <span className="mr-1.5 font-mono text-[12px]" style={{ color: "var(--accent-bright)" }}>
                  {i + 1}.
                </span>
              )}
              {renderInline(item, `${key}-${i}`)}
            </span>
          </li>
        ))}
      </ul>
    );
    list = null;
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*]\s+(.*)/);
    const num = line.match(/^\s*\d+\.\s+(.*)/);
    const heading = line.match(/^(#{1,3})\s+(.*)/);

    if (bullet) {
      if (list?.type !== "ul") {
        flush(`f${idx}`);
        list = { type: "ul", items: [] };
      }
      list.items.push(bullet[1]);
      return;
    }
    if (num) {
      if (list?.type !== "ol") {
        flush(`f${idx}`);
        list = { type: "ol", items: [] };
      }
      list.items.push(num[1]);
      return;
    }

    flush(`f${idx}`);

    if (heading) {
      blocks.push(
        <div key={idx} className="pt-1 text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
          {renderInline(heading[2], `h${idx}`)}
        </div>
      );
      return;
    }
    if (line.trim() === "") {
      blocks.push(<div key={idx} style={{ height: 4 }} />);
      return;
    }
    blocks.push(
      <p key={idx} className="leading-[1.65]" style={{ margin: 0 }}>
        {renderInline(line, `p${idx}`)}
      </p>
    );
  });
  flush("fend");

  return (
    <div className="space-y-1 text-[13.5px]" style={{ color: "var(--text-secondary)" }}>
      {blocks}
    </div>
  );
}

function MetricWidget({ data }: { data: Record<string, unknown> }) {
  const grr = data.grr_pct as number;
  const verdict = data.verdict as string;
  const evPct = data.ev_pct as number;
  const avPct = data.av_pct as number;
  const ndc = data.ndc as number;

  return (
    <div
      className="mt-4 rounded-xl p-4"
      style={{
        background: "var(--bg-elevated)",
        border: `1px solid ${verdict === "unacceptable" ? "rgba(248,113,113,0.18)" : "var(--border-subtle)"}`,
      }}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="section-label">GR&amp;R Result</span>
        <span
          className={`badge ${
            verdict === "acceptable" ? "badge-success" : verdict === "conditional" ? "badge-warning" : "badge-critical"
          }`}
        >
          {verdict === "acceptable" ? <CheckCircle2 size={9} /> : verdict === "conditional" ? <AlertTriangle size={9} /> : <XCircle size={9} />}
          {verdict}
        </span>
      </div>
      <div className="mb-3 flex items-end gap-3">
        <span
          className="stat-number text-4xl"
          style={{
            color: verdict === "acceptable" ? "var(--success-text)" : verdict === "conditional" ? "var(--warning-text)" : "var(--critical-text)",
          }}
        >
          {grr}%
        </span>
        <span className="pb-1.5 text-[11px]" style={{ color: "var(--text-muted)" }}>
          total GR&amp;R
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "EV %", value: `${evPct}%`, sub: "Repeatability" },
          { label: "AV %", value: `${avPct}%`, sub: "Reproducibility" },
          { label: "NDC", value: ndc?.toString(), sub: ndc >= 5 ? "Adequate" : "Low" },
        ].map((m, i) => (
          <div key={i} className="panel-inset p-2.5">
            <div className="text-[9px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-ghost)" }}>
              {m.label}
            </div>
            <div className="stat-number mt-0.5 text-sm" style={{ color: "var(--text-primary)" }}>
              {m.value}
            </div>
            <div className="text-[9px]" style={{ color: "var(--text-ghost)" }}>
              {m.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Work-log step row (shared by live console + persisted trace) ─────────────

// Result readout that counts up like an instrument when it first appears.
function ResultChip({ text }: { text: string }) {
  const match = /^(\d+)\s+(.*)$/.exec(text);
  const target = match ? parseInt(match[1], 10) : 0;
  const [val, setVal] = useState(match ? 0 : target);

  useEffect(() => {
    if (!match) return;
    const start = performance.now();
    const dur = 560;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      setVal(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    // Guarantee the final value even if rAF is throttled (e.g. backgrounded tab).
    const settle = window.setTimeout(() => setVal(target), dur + 80);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(settle);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <span className="agent-chip">{match ? `${val} ${match[2]}` : text}</span>;
}

function StepRow({ step }: { step: TraceStep }) {
  const Glyph = STEP_GLYPHS[step.id];
  const isActive = step.status === "active";
  const isDone = step.status === "done";
  const isSkipped = step.status === "skipped";
  const elapsed = isActive && step.startedAt ? ((performance.now() - step.startedAt) / 1000).toFixed(1) : "0.0";

  return (
    <div className="agent-row agent-line" data-status={step.status}>
      <span className="agent-conn">
        <i />
      </span>
      <div className="agent-gut">
        <span className="agent-seat">
          <span className="agent-pr" />
          <span className="agent-scan" />
          <span className="agent-glyph">
            <Glyph size={16} />
          </span>
        </span>
      </div>
      <div className="agent-meta">
        <div className="agent-lbl">{isActive ? step.active : step.label}</div>
        <div className="agent-det">{step.detail}</div>
      </div>
      <div className="agent-state">
        {isActive && <span className="agent-tmr">{elapsed}s</span>}
        {isDone && step.result && <ResultChip text={step.result} />}
        {isSkipped && <span className="agent-skip">n/a</span>}
      </div>
    </div>
  );
}

function AgentConsole({ steps, elapsed }: { steps: TraceStep[]; elapsed: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-4">
      <div className="mt-1 shrink-0">
        <AgentCore size={36} state="thinking" />
      </div>
      <div className="min-w-0 flex-1 overflow-hidden rounded-2xl elevated-card" style={{ padding: "14px 14px 10px" }}>
        <div className="mb-2 flex items-center gap-2.5 px-1">
          <span className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
            Agent is working
          </span>
          <span className="h-1 w-1 rounded-full" style={{ background: "var(--text-ghost)" }} />
          <span className="stat-number text-[11px]" style={{ color: "var(--text-muted)" }}>
            {elapsed.toFixed(1)}s
          </span>
          <span className="section-label ml-auto text-[9px]">Live trace</span>
        </div>
        <div>
          {steps.map((s) => (
            <StepRow key={s.id} step={s} />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function TraceSummary({ trace }: { trace: AgentTrace }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-2.5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="group inline-flex items-center gap-2 rounded-full py-1 pl-1 pr-2.5 transition-colors"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}
      >
        <span className="flex h-5 w-5 items-center justify-center rounded-full" style={{ background: "var(--success-bg)", color: "var(--success-text)" }}>
          <GlyphCheck size={12} />
        </span>
        <span className="text-[11.5px] font-medium" style={{ color: "var(--text-secondary)" }}>
          Reasoned for {(trace.durationMs / 1000).toFixed(1)}s
        </span>
        <span className="h-1 w-1 rounded-full" style={{ background: "var(--text-ghost)" }} />
        <span className="text-[11.5px]" style={{ color: "var(--text-muted)" }}>
          {trace.sources.length} source{trace.sources.length === 1 ? "" : "s"}
        </span>
        <ChevronDown size={13} className="transition-transform duration-200" style={{ color: "var(--text-muted)", transform: open ? "rotate(180deg)" : "none" }} />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }} className="overflow-hidden">
            <div className="panel-inset mt-2 p-2">
              <div>
                {trace.steps.map((s) => (
                  <StepRow key={s.id} step={s} />
                ))}
              </div>
              {trace.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t px-1 pt-2.5" style={{ borderColor: "var(--border-subtle)" }}>
                  <span className="section-label mr-0.5 text-[9px]">Context</span>
                  {trace.sources.map((src) => (
                    <span
                      key={src}
                      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[10.5px] font-medium"
                      style={{ background: "var(--accent-bg)", color: "var(--accent-bright)", border: "1px solid rgba(78,140,255,0.18)" }}
                    >
                      <GlyphSource size={12} />
                      {SOURCE_LABEL[src] || src}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [messages, setMessages] = useState<AgentMessage[]>(ALLOW_MOCK ? (exampleChat as AgentMessage[]) : []);
  const [input, setInput] = useState("");
  const [liveSteps, setLiveSteps] = useState<TraceStep[] | null>(null);
  const [liveAnswer, setLiveAnswer] = useState("");
  const [, setTick] = useState(0);

  const scrollRef = useRef<HTMLDivElement>(null);
  const busyRef = useRef(false);
  const runStartRef = useRef(0);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const { pendingChatPrompt, setPendingChatPrompt } = useAppStore();

  const thinking = liveSteps !== null;
  const elapsed = thinking ? (performance.now() - runStartRef.current) / 1000 : 0;

  // Live total timer while the agent works.
  useEffect(() => {
    if (!thinking) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 100);
    return () => window.clearInterval(id);
  }, [thinking]);

  const sendMessage = useCallback(async (prompt: string) => {
    const userText = prompt.trim();
    if (!userText || busyRef.current) return;
    busyRef.current = true;

    const userMsg: AgentMessage = { id: `u-${Date.now()}`, role: "user", content: userText, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const history = messagesRef.current
      .filter((m) => m.id !== "welcome" && !m.isError)
      .map((m) => ({ role: m.role, content: m.content }));

    const steps = makeSteps();
    const idxById: Record<string, number> = {};
    steps.forEach((s, i) => (idxById[s.id] = i));

    const start = performance.now();
    runStartRef.current = start;
    setLiveSteps(steps.map((s) => ({ ...s })));
    setLiveAnswer("");

    const patch = (i: number, p: Partial<TraceStep>) => {
      steps[i] = { ...steps[i], ...p };
      setLiveSteps(steps.map((s) => ({ ...s })));
    };

    // "Parse request" is the only client-side node: active from the instant we
    // send, resolved the moment the backend's first real event lands.
    patch(idxById.parse, { status: "active", startedAt: performance.now() });

    let answer = "";            // full text accumulated from delta events
    let shown = 0;              // chars currently revealed (typewriter smoothing)
    let revealing = true;
    let rafId = 0;
    let finalSources: string[] = [];
    let finalMs = 0;
    let parseClosed = false;
    const closeParse = () => {
      if (parseClosed) return;
      parseClosed = true;
      patch(idxById.parse, { status: "done", result: "intent locked" });
    };

    // Gemini streams a few large chunks; reveal them at a steady character rate
    // so the answer types in smoothly instead of arriving in visible jumps.
    const reveal = () => {
      if (shown < answer.length) {
        const remaining = answer.length - shown;
        shown = Math.min(answer.length, shown + Math.max(2, Math.ceil(remaining / 9)));
        setLiveAnswer(answer.slice(0, shown));
      }
      if (revealing) rafId = requestAnimationFrame(reveal);
    };
    rafId = requestAnimationFrame(reveal);

    // Every event here is a real operation the backend just performed.
    const onEvent = (ev: AgentStreamEvent) => {
      if (ev.t === "step") {
        closeParse();
        const i = idxById[ev.id];
        if (i == null) return;
        if (ev.phase === "start") {
          patch(i, {
            status: "active",
            startedAt: performance.now(),
            ...(ev.label ? { active: ev.label } : {}),
            ...(ev.detail ? { detail: ev.detail } : {}),
          });
        } else {
          patch(i, { status: ev.status === "skipped" ? "skipped" : "done", result: ev.result });
        }
      } else if (ev.t === "delta") {
        closeParse();
        answer += ev.text;
      } else if (ev.t === "final") {
        answer = ev.answer || answer;
        finalSources = ev.sources || [];
        finalMs = ev.ms || Math.round(performance.now() - start);
      }
    };

    const pushAssistant = (content: string, opts: { sources: string[]; durationMs: number } | { isError: true }) => {
      const finalSteps = steps.map((s) => (s.status === "active" ? { ...s, status: "done" as StepStatus } : s));
      const msg: AgentMessage =
        "isError" in opts
          ? { id: `a-${Date.now()}`, role: "assistant", content, timestamp: new Date(), isError: true }
          : { id: `a-${Date.now()}`, role: "assistant", content, timestamp: new Date(), trace: { steps: finalSteps, durationMs: opts.durationMs, sources: opts.sources } };
      setMessages((prev) => [...prev, msg]);
    };

    try {
      await streamChat({ question: userText, conversation_history: history }, onEvent);
      pushAssistant(answer || "I received an empty response.", {
        sources: finalSources,
        durationMs: finalMs || Math.round(performance.now() - start),
      });
    } catch {
      // Keep any text already streamed; otherwise fall back to the
      // non-streaming endpoint so older backends still answer.
      if (answer) {
        pushAssistant(answer, { sources: finalSources, durationMs: Math.round(performance.now() - start) });
      } else {
        try {
          const d = await apiClient.post<{ answer: string; context_used: string[] }>("/api/v1/chat", {
            question: userText,
            conversation_history: history,
          });
          const sources = d.context_used || [];
          steps.forEach((s, i) => {
            if (s.source) {
              const hit = sources.includes(s.source);
              patch(i, { status: hit ? "done" : "skipped", result: hit ? s.result ?? "consulted" : "n/a" });
            } else {
              patch(i, { status: "done" });
            }
          });
          pushAssistant(d.answer || "I received an empty response.", {
            sources,
            durationMs: Math.round(performance.now() - start),
          });
        } catch {
          pushAssistant(
            "**Couldn't reach the agent backend.** Make sure the FastAPI server is running on port 8000, then try again.",
            { isError: true }
          );
        }
      }
    } finally {
      revealing = false;
      if (rafId) cancelAnimationFrame(rafId);
      setLiveSteps(null);
      setLiveAnswer("");
      busyRef.current = false;
    }
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, liveSteps, liveAnswer]);

  useEffect(() => {
    if (!pendingChatPrompt) return;
    const timer = window.setTimeout(() => {
      void sendMessage(pendingChatPrompt);
      setPendingChatPrompt("");
    }, 0);
    return () => window.clearTimeout(timer);
  }, [pendingChatPrompt, sendMessage, setPendingChatPrompt]);

  const handleCopy = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      showToast("Copied to clipboard.");
    } catch {
      showToast("Copy failed.");
    }
  };

  const handleRegenerate = async () => {
    const last = [...messages].reverse().find((m) => m.role === "user");
    if (!last) return showToast("Nothing to regenerate yet.");
    await sendMessage(last.content);
  };

  const isEmpty = messages.length === 0 && !thinking;

  return (
    <div className="flex h-full flex-col" style={{ background: "var(--bg-root)" }}>
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b px-8 py-5" style={{ borderColor: "var(--border-subtle)" }}>
        <div className="flex items-center gap-3.5">
          <AgentCore size={40} state={thinking ? "thinking" : "idle"} />
          <div>
            <h1 className="text-display text-[17px] font-semibold leading-tight" style={{ color: "var(--text-primary)" }}>
              Quality AI Intelligence Agent
            </h1>
            <p className="mt-0.5 text-[11.5px]" style={{ color: "var(--text-muted)" }}>
              Gemini reasoning · live system context
            </p>
          </div>
        </div>
        <div
          className="flex h-7 items-center gap-2 rounded-full border px-3"
          style={{ borderColor: thinking ? "var(--border-accent)" : "rgba(16,185,129,0.22)", background: thinking ? "var(--accent-bg)" : "var(--success-bg)" }}
        >
          <span className={thinking ? "" : "live-dot"} style={{ width: 6, height: 6, borderRadius: "50%", background: thinking ? "var(--accent)" : undefined }} />
          <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: thinking ? "var(--accent-bright)" : "var(--success-text)" }}>
            {thinking ? "Thinking" : "Ready"}
          </span>
        </div>
      </div>

      {/* Conversation */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div className="flex h-full flex-col items-center justify-center px-6 py-10 text-center">
            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}>
              <AgentCore size={140} state="idle" />
            </motion.div>
            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-display gradient-text mt-8 text-[30px] font-semibold leading-tight md:text-[34px]"
              style={{ letterSpacing: "-0.02em" }}
            >
              Quality intelligence, on call.
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.16 }}
              className="mt-3.5 max-w-md text-[14px] leading-relaxed"
              style={{ color: "var(--text-muted)" }}
            >
              Ask in plain language. The agent reads your live GR&amp;R studies, SPC monitors, and open alerts — then shows its work.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.24 }}
              className="mt-10 grid w-full max-w-2xl grid-cols-1 gap-2.5 text-left sm:grid-cols-2"
            >
              {SUGGESTIONS.map(({ q, g: G }, i) => (
                <button
                  key={i}
                  onClick={() => void sendMessage(q)}
                  className="surface-card group flex items-center gap-3 px-4 py-3.5"
                >
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors"
                    style={{ background: "var(--accent-bg)", color: "var(--accent-bright)", border: "1px solid rgba(78,140,255,0.16)" }}
                  >
                    <G size={18} />
                  </span>
                  <span className="min-w-0 flex-1 text-[13px] leading-snug" style={{ color: "var(--text-secondary)" }}>
                    {q}
                  </span>
                  <ArrowUpRight size={15} className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100" style={{ color: "var(--text-muted)" }} />
                </button>
              ))}
            </motion.div>
          </div>
        ) : (
          <div className="mx-auto w-full max-w-3xl space-y-8 px-6 py-8">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
                  className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  {/* Avatar */}
                  <div className="mt-0.5 shrink-0">
                    {msg.role === "assistant" ? (
                      <AgentCore size={34} state="idle" animated={false} />
                    ) : (
                      <div
                        className="flex h-9 w-9 items-center justify-center rounded-xl"
                        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}
                      >
                        <User size={15} style={{ color: "var(--text-muted)" }} />
                      </div>
                    )}
                  </div>

                  {/* Body */}
                  <div className={`flex min-w-0 max-w-[calc(100%-3.5rem)] flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
                    {msg.role === "assistant" && msg.trace && <TraceSummary trace={msg.trace} />}

                    <div
                      className="rounded-2xl px-5 py-4"
                      style={{
                        background: msg.role === "user" ? "var(--accent-bg-strong)" : msg.isError ? "var(--critical-bg)" : "var(--bg-surface)",
                        border: `1px solid ${msg.role === "user" ? "rgba(78,140,255,0.2)" : msg.isError ? "rgba(248,113,113,0.25)" : "var(--border-subtle)"}`,
                        color: msg.role === "user" ? "var(--text-primary)" : undefined,
                      }}
                    >
                      {msg.role === "user" ? (
                        <p className="text-[13.5px] leading-relaxed" style={{ color: "var(--text-primary)" }}>
                          {msg.content}
                        </p>
                      ) : (
                        <MarkdownText content={msg.content} />
                      )}

                      {msg.widgets?.map((widget, i) => (
                        <div key={i}>{widget.type === "metric" && <MetricWidget data={widget.data} />}</div>
                      ))}
                    </div>

                    {/* Assistant action bar */}
                    {msg.role === "assistant" && !msg.isError && (
                      <div className="mt-2 flex items-center gap-0.5 pl-1">
                        {[
                          { icon: Copy, label: "Copy", onClick: () => void handleCopy(msg.content) },
                          { icon: ThumbsUp, label: "Helpful", onClick: () => showToast("Thanks for the feedback.") },
                          { icon: ThumbsDown, label: "Not helpful", onClick: () => showToast("Feedback recorded.") },
                          { icon: RotateCcw, label: "Regenerate", onClick: () => void handleRegenerate() },
                        ].map(({ icon: Icon, label, onClick }) => (
                          <button
                            key={label}
                            onClick={onClick}
                            title={label}
                            className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--bg-elevated)]"
                            style={{ color: "var(--text-ghost)" }}
                          >
                            <Icon size={13} />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Live work-log */}
            <AnimatePresence>{liveSteps && <AgentConsole steps={liveSteps} elapsed={elapsed} />}</AnimatePresence>

            {/* Live answer — types in token-by-token as Gemini streams */}
            {liveAnswer && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-4">
                <div className="mt-0.5 shrink-0">
                  <AgentCore size={34} state="thinking" />
                </div>
                <div className="flex min-w-0 max-w-[calc(100%-3.5rem)] flex-col items-start">
                  <div
                    className="rounded-2xl px-5 py-4"
                    style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}
                  >
                    <MarkdownText content={liveAnswer} />
                    <span className="agent-caret" />
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="shrink-0 px-6 pb-5 pt-2">
        <div className="mx-auto w-full max-w-3xl">
          <div
            className="flex items-end gap-3 rounded-2xl px-4 py-3 transition-colors"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", boxShadow: "var(--shadow-md)" }}
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void sendMessage(input);
                }
              }}
              placeholder={thinking ? "Agent is working…" : "Ask about GR&R studies, SPC violations, alerts…"}
              rows={1}
              disabled={thinking}
              className="max-h-[140px] min-h-[28px] flex-1 resize-none bg-transparent text-[14px] leading-relaxed outline-none"
              style={{ color: "var(--text-primary)" }}
            />
            <motion.button
              whileTap={{ scale: 0.94 }}
              onClick={() => void sendMessage(input)}
              disabled={!input.trim() || thinking}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-all"
              style={{
                background: input.trim() && !thinking ? "var(--gradient-accent)" : "var(--bg-elevated)",
                color: input.trim() && !thinking ? "white" : "var(--text-ghost)",
                boxShadow: input.trim() && !thinking ? "inset 0 1px 0 rgba(255,255,255,0.2), 0 2px 10px -2px rgba(47,106,224,0.5)" : "none",
                cursor: input.trim() && !thinking ? "pointer" : "default",
              }}
            >
              <ArrowUp size={17} strokeWidth={2.4} />
            </motion.button>
          </div>
          <p className="mt-2.5 text-center text-[10.5px]" style={{ color: "var(--text-ghost)" }}>
            Answers draw on live system data. Verify critical decisions against raw measurements.
          </p>
        </div>
      </div>
    </div>
  );
}
