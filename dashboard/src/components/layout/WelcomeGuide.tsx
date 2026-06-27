"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Activity,
  UploadCloud,
  FlaskConical,
  Bell,
  Sparkles,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { useAppStore } from "@/lib/store";

const ONBOARDED_KEY = "arad-onboarded";

type Step = {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  body: string;
  cta: string;
  page: string;
};

const STEPS: Step[] = [
  {
    icon: Activity,
    title: "We watch your quality for you",
    body: "Overview, SPC Monitor and Alert Inbox show live status. The app monitors your measurements around the clock and flags problems — you don't have to go looking.",
    cta: "Open Overview",
    page: "dashboard",
  },
  {
    icon: UploadCloud,
    title: "Get your data in",
    body: "The easiest way is to upload a spreadsheet (CSV or Excel) from any machine or gauge. Or have IT connect your MES/QMS once — then data flows in on its own.",
    cta: "Add data",
    page: "integrations",
  },
  {
    icon: FlaskConical,
    title: "Run studies & manage gages",
    body: "Step-by-step GR&R studies and a gage registry, built around how quality engineers already work — paste from Excel, load a sample, no setup required.",
    cta: "Open GR&R Studies",
    page: "grr",
  },
  {
    icon: Bell,
    title: "Choose where alerts go",
    body: "Send alerts to Slack, email, or text so the right people hear about problems fast. You set this once in Connections — no technical keys needed for the basics.",
    cta: "Set up alerts",
    page: "integrations",
  },
];

export default function WelcomeGuide() {
  const welcomeOpen = useAppStore((s) => s.welcomeOpen);
  const setWelcomeOpen = useAppStore((s) => s.setWelcomeOpen);
  const setActivePage = useAppStore((s) => s.setActivePage);

  // Show automatically the very first time, then never again unless reopened
  // from the "Getting started" button.
  useEffect(() => {
    try {
      if (!window.localStorage.getItem(ONBOARDED_KEY)) {
        setWelcomeOpen(true);
      }
    } catch {
      /* storage unavailable — skip the auto-open, the button still works */
    }
  }, [setWelcomeOpen]);

  const close = () => {
    try {
      window.localStorage.setItem(ONBOARDED_KEY, "1");
    } catch {
      /* ignore */
    }
    setWelcomeOpen(false);
  };

  const goTo = (page: string) => {
    setActivePage(page);
    close();
  };

  return (
    <AnimatePresence>
      {welcomeOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={close}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0, 0, 0, 0.7)" }}
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-xl)",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            {/* Header */}
            <div
              className="edge-glow relative shrink-0 px-6 py-5"
              style={{ borderBottom: "1px solid var(--border-subtle)" }}
            >
              <button onClick={close} className="btn-icon absolute right-4 top-4" aria-label="Close">
                <X size={17} />
              </button>
              <div className="flex items-center gap-3">
                <span
                  className="flex h-11 w-11 items-center justify-center rounded-xl border"
                  style={{
                    borderColor: "var(--accent-bg-strong)",
                    background: "var(--accent-bg)",
                    color: "var(--accent-bright)",
                    boxShadow: "0 0 24px -6px rgba(78,140,255,0.5), inset 0 1px 0 rgba(255,255,255,0.08)",
                  }}
                >
                  <Sparkles size={20} />
                </span>
                <div>
                  <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                    Welcome to Quality AI Intelligence
                  </h2>
                  <p className="mt-0.5 text-sm" style={{ color: "var(--text-secondary)" }}>
                    Your quality command center — built for engineers, not coders. Here's the whole app in four steps.
                  </p>
                </div>
              </div>
            </div>

            {/* Steps */}
            <div className="grid gap-2.5 overflow-y-auto px-6 py-5 sm:grid-cols-2">
              {STEPS.map((step, i) => {
                const Icon = step.icon;
                return (
                  <button
                    key={step.title}
                    onClick={() => goTo(step.page)}
                    className="group flex flex-col rounded-xl border p-4 text-left transition-colors hover:border-[var(--border-accent)]"
                    style={{ borderColor: "var(--border-default)", background: "var(--bg-primary)" }}
                  >
                    <div className="mb-2.5 flex items-center gap-2.5">
                      <span
                        className="flex h-8 w-8 items-center justify-center rounded-lg border text-[var(--accent-bright)]"
                        style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)" }}
                      >
                        <Icon size={15} />
                      </span>
                      <span
                        className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em]"
                        style={{ color: "var(--text-ghost)" }}
                      >
                        Step {i + 1}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      {step.title}
                    </h3>
                    <p className="mt-1 flex-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                      {step.body}
                    </p>
                    <span
                      className="mt-3 inline-flex items-center gap-1 text-xs font-medium transition-transform group-hover:translate-x-0.5"
                      style={{ color: "var(--accent-bright)" }}
                    >
                      {step.cta} <ArrowRight size={13} />
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Footer */}
            <div
              className="shrink-0 px-6 py-4"
              style={{ borderTop: "1px solid var(--border-subtle)", background: "var(--bg-primary)" }}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  <ShieldCheck size={14} style={{ color: "var(--success)" }} />
                  No setup keys to chase — the app connects to your server automatically.
                </p>
                <button onClick={close} className="btn btn-primary shrink-0">
                  Got it — let&apos;s go
                </button>
              </div>
              <p className="mt-2.5 text-[11px]" style={{ color: "var(--text-ghost)" }}>
                You can reopen this anytime from <strong>Getting started</strong> at the bottom of the sidebar.
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
