"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  KeyRound,
  Globe,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Plug,
  ChevronDown,
  Wrench,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import {
  API_BASE_URL_STORAGE_KEY,
  API_KEY_STORAGE_KEY,
  resolveApiBaseUrl,
  resolveApiKey,
  showToast,
} from "@/api/apiClient";
import { useAppStore } from "@/lib/store";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ConnectionState = "idle" | "checking" | "ok" | "failed";

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [connection, setConnection] = useState<ConnectionState>("idle");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const setActivePage = useAppStore((s) => s.setActivePage);

  const goToIntegrations = () => {
    setActivePage("integrations");
    onClose();
  };

  const testConnection = async (url?: string) => {
    const target = (url ?? baseUrl).trim().replace(/\/$/, "");
    if (!target) {
      setConnection("failed");
      return;
    }
    setConnection("checking");
    try {
      const response = await fetch(`${target}/health/live`, {
        signal: AbortSignal.timeout(5000),
      });
      setConnection(response.ok ? "ok" : "failed");
    } catch {
      setConnection("failed");
    }
  };

  useEffect(() => {
    if (isOpen) {
      const url = resolveApiBaseUrl();
      setBaseUrl(url);
      setApiKey(resolveApiKey());
      setAdvancedOpen(false);
      // Check automatically so the engineer just sees the result — no button to hunt for.
      void testConnection(url);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const save = () => {
    const trimmedUrl = baseUrl.trim().replace(/\/$/, "");
    if (!trimmedUrl) {
      showToast("Server address can't be empty.");
      return;
    }

    window.localStorage.setItem(API_BASE_URL_STORAGE_KEY, trimmedUrl);
    if (apiKey.trim()) {
      window.localStorage.setItem(API_KEY_STORAGE_KEY, apiKey.trim());
    } else {
      window.localStorage.removeItem(API_KEY_STORAGE_KEY);
    }

    showToast("Saved. The dashboard will use this server address from now on.");
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0, 0, 0, 0.65)" }}
        >
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.18 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md overflow-hidden"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-xl)",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <div
              className="flex items-center justify-between border-b px-5 py-4"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <div>
                <h2 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                  Settings
                </h2>
                <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                  Your connection status and where to set things up
                </p>
              </div>
              <button onClick={onClose} className="btn-icon" aria-label="Close settings">
                <X size={17} />
              </button>
            </div>

            <div className="space-y-3 px-5 py-5">
              {/* Connection status — the engineer just sees the result, no jargon */}
              <div
                className="rounded-xl border px-4 py-3.5"
                style={{
                  borderColor:
                    connection === "ok"
                      ? "rgba(16,185,129,0.25)"
                      : connection === "failed"
                        ? "rgba(239,68,68,0.25)"
                        : "var(--border-default)",
                  background:
                    connection === "ok"
                      ? "var(--success-bg)"
                      : connection === "failed"
                        ? "var(--critical-bg)"
                        : "var(--bg-primary)",
                }}
              >
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 shrink-0">
                    {connection === "checking" ? (
                      <Loader2 size={18} className="animate-spin" style={{ color: "var(--text-muted)" }} />
                    ) : connection === "ok" ? (
                      <CheckCircle2 size={18} style={{ color: "var(--success)" }} />
                    ) : connection === "failed" ? (
                      <AlertTriangle size={18} style={{ color: "var(--critical)" }} />
                    ) : (
                      <ShieldCheck size={18} style={{ color: "var(--text-muted)" }} />
                    )}
                  </span>
                  <div className="min-w-0">
                    <p
                      className="text-sm font-semibold"
                      style={{
                        color:
                          connection === "ok"
                            ? "var(--success-text)"
                            : connection === "failed"
                              ? "var(--critical-text)"
                              : "var(--text-primary)",
                      }}
                    >
                      {connection === "checking"
                        ? "Checking your connection…"
                        : connection === "ok"
                          ? "Connected to your quality server"
                          : connection === "failed"
                            ? "Can't reach your quality server right now"
                            : "Connection"}
                    </p>
                    <p className="mt-0.5 text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      {connection === "ok"
                        ? "Everything's working — there's nothing you need to set up here."
                        : connection === "failed"
                          ? "This is usually a server or network issue, not something you need to fix in the app. Ask your IT administrator to check the quality server is running."
                          : "Making sure the dashboard can talk to your quality server."}
                    </p>
                  </div>
                </div>
              </div>

              {/* The thing a quality engineer actually comes here to do */}
              <button
                onClick={goToIntegrations}
                className="flex w-full items-center gap-3 rounded-xl border px-4 py-3.5 text-left transition-colors hover:border-[var(--border-accent)]"
                style={{ borderColor: "var(--border-default)", background: "var(--bg-primary)" }}
              >
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border"
                  style={{
                    borderColor: "var(--accent-bg-strong)",
                    background: "var(--accent-bg)",
                    color: "var(--accent-bright)",
                  }}
                >
                  <Plug size={16} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    Set up alerts &amp; connect your tools
                  </span>
                  <span className="mt-0.5 block text-xs" style={{ color: "var(--text-muted)" }}>
                    Choose where alerts go (Slack, email, text) and connect your data
                  </span>
                </span>
                <span className="text-sm font-medium" style={{ color: "var(--accent-bright)" }}>
                  Open →
                </span>
              </button>

              {/* Advanced — collapsed by default, clearly for IT */}
              <div
                className="overflow-hidden rounded-xl border"
                style={{ borderColor: "var(--border-subtle)", background: "var(--bg-primary)" }}
              >
                <button
                  onClick={() => setAdvancedOpen((v) => !v)}
                  className="flex w-full items-center gap-2.5 px-4 py-3 text-left"
                  aria-expanded={advancedOpen}
                >
                  <Wrench size={14} style={{ color: "var(--text-muted)" }} />
                  <span className="flex-1 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                    Advanced · for IT administrators
                  </span>
                  <ChevronDown
                    size={15}
                    style={{
                      color: "var(--text-muted)",
                      transform: advancedOpen ? "rotate(180deg)" : "none",
                      transition: "transform 0.18s ease",
                    }}
                  />
                </button>

                <AnimatePresence initial={false}>
                  {advancedOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: "easeOut" }}
                    >
                      <div className="space-y-4 border-t px-4 py-4" style={{ borderColor: "var(--border-subtle)" }}>
                        <p className="text-[11px] leading-relaxed" style={{ color: "var(--text-ghost)" }}>
                          Most people should leave this alone — the dashboard finds your server automatically.
                          These settings only matter when IT hosts the quality server at a custom address.
                        </p>

                        <label className="block">
                          <span
                            className="mb-1.5 flex items-center gap-1.5 text-xs font-medium"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            <Globe size={13} /> Server address
                          </span>
                          <input
                            value={baseUrl}
                            onChange={(e) => {
                              setBaseUrl(e.target.value);
                              setConnection("idle");
                            }}
                            className="input-field"
                            placeholder="http://127.0.0.1:8000"
                            spellCheck={false}
                          />
                        </label>

                        <label className="block">
                          <span
                            className="mb-1.5 flex items-center gap-1.5 text-xs font-medium"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            <KeyRound size={13} /> Access key
                          </span>
                          <input
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            className="input-field"
                            placeholder="Only needed if IT gave you one"
                            type="password"
                            autoComplete="off"
                            spellCheck={false}
                          />
                          <span className="mt-1.5 block text-[11px]" style={{ color: "var(--text-ghost)" }}>
                            This is the key that lets the dashboard talk to your server — <em>not</em> a Slack,
                            email, or AI key. Those live in Integrations.
                          </span>
                        </label>

                        <button
                          onClick={() => void testConnection()}
                          className="btn btn-secondary"
                          disabled={connection === "checking"}
                        >
                          {connection === "checking" ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <RefreshCw size={14} />
                          )}
                          Recheck connection
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div
              className="flex justify-end gap-2 border-t px-5 py-4"
              style={{ borderColor: "var(--border-subtle)", background: "var(--bg-primary)" }}
            >
              {advancedOpen ? (
                <>
                  <button onClick={onClose} className="btn btn-ghost">
                    Cancel
                  </button>
                  <button onClick={save} className="btn btn-primary">
                    Save changes
                  </button>
                </>
              ) : (
                <button onClick={onClose} className="btn btn-primary">
                  Done
                </button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
