"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import HelpTip from "@/components/ui/HelpTip";
import {
  Workflow,
  Plus,
  Trash2,
  MessageSquare,
  Mail,
  Smartphone,
  Ticket,
  Database,
  ArrowRight,
  Zap,
  Power,
} from "lucide-react";
import {
  createAlertRule,
  deleteAlertRule,
  getAlertRules,
  getSettings,
  showToast,
  updateAlertRule,
  type AlertRuleRecord,
} from "@/api/apiClient";
import { useAppStore } from "@/lib/store";

type ChannelKind = "chat" | "email" | "sms" | "ticket" | "data";
// `configured` = keys saved on the server; `verified` = those keys passed a live
// test. A channel is only trustworthy as an alert destination when verified.
type Channel = { id: string; name: string; detail: string; kind: ChannelKind; enabled: boolean; configured: boolean; verified?: boolean };

type TriggerId = "grr_fail" | "spc_violation" | "calibration_overdue" | "pass_rate_below";
type AlertRule = {
  id: string;
  name: string;
  trigger: TriggerId;
  threshold?: number;
  scope: string;
  channels: string[];
  enabled: boolean;
};

const CHANNELS_KEY = "arad-integrations";
const RULES_KEY = "arad-alert-rules";
const TESTS_KEY = "arad-integration-tests"; // shared with Data & Integrations

const DEFAULT_CHANNELS: Channel[] = [
  { id: "slack", name: "Slack", detail: "#quality-alerts", kind: "chat", enabled: true, configured: true },
  { id: "email", name: "Email", detail: "quality-team@arad.io", kind: "email", enabled: true, configured: true },
  { id: "sms", name: "SMS", detail: "On-call supervisor", kind: "sms", enabled: false, configured: false },
  { id: "jira", name: "JIRA", detail: "QUAL project", kind: "ticket", enabled: false, configured: true },
  { id: "qms", name: "QMS", detail: "Inspection equipment sync", kind: "data", enabled: true, configured: true },
  { id: "mes", name: "MES feed", detail: "Real-time measurements", kind: "data", enabled: true, configured: true },
];

const TRIGGERS: Record<TriggerId, string> = {
  grr_fail: "GR&R study fails (> 30%)",
  spc_violation: "SPC violation detected",
  calibration_overdue: "Calibration overdue",
  pass_rate_below: "Pass rate falls below…",
};

const SAMPLE_RULES: Omit<AlertRule, "id">[] = [
  { name: "GR&R failure escalation", trigger: "grr_fail", scope: "Any gage", channels: ["slack", "sms"], enabled: true },
  { name: "SPC out-of-control", trigger: "spc_violation", scope: "Any process", channels: ["slack", "email"], enabled: true },
];

const CHANNEL_ICON: Record<ChannelKind, React.ComponentType<{ size?: number; className?: string }>> = {
  chat: MessageSquare,
  email: Mail,
  sms: Smartphone,
  ticket: Ticket,
  data: Database,
};

// Only message/escalation channels can be picked as alert destinations.
const NOTIFY_CHANNELS = ["slack", "email", "sms", "jira"];

function loadJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

/** Map a server alert-rule record to the page's local shape. */
function fromApiRule(r: AlertRuleRecord): AlertRule {
  return {
    id: r.id,
    name: r.name,
    trigger: r.trigger as TriggerId,
    threshold: r.threshold ?? undefined,
    scope: r.scope,
    channels: r.channels ?? [],
    enabled: r.enabled,
  };
}

export default function AlertRulesPage() {
  const [channels, setChannels] = useState<Channel[]>(DEFAULT_CHANNELS);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState<Omit<AlertRule, "id">>({ name: "", trigger: "grr_fail", scope: "Any gage", channels: ["slack"], enabled: true, threshold: undefined });
  const setActivePage = useAppStore((s) => s.setActivePage);

  const refreshRules = useCallback(async () => {
    try {
      const data = await getAlertRules();
      const mapped = data.map(fromApiRule);
      setRules(mapped);
      try { window.localStorage.setItem(RULES_KEY, JSON.stringify(mapped)); } catch {}
    } catch {
      setRules(loadJson<AlertRule[]>(RULES_KEY, []));
    }
  }, []);

  useEffect(() => {
    setChannels(loadJson<Channel[]>(CHANNELS_KEY, DEFAULT_CHANNELS));
    setRules(loadJson<AlertRule[]>(RULES_KEY, []));
    void refreshRules();
  }, [refreshRules]);

  // Reconcile each channel against Data & Integrations: `configured` = keys saved
  // on the server, `verified` = those keys passed a live Test. A channel can only
  // be enabled or used as an alert destination once VERIFIED — saving a wrong
  // Slack webhook leaves it "configured" but unverified, so it stays blocked.
  useEffect(() => {
    let cancelled = false;
    void getSettings()
      .then((res) => {
        if (cancelled) return;
        // Server-side test results are authoritative; localStorage is the offline fallback.
        const tests = res.tests ?? loadJson<Record<string, { ok: boolean }>>(TESTS_KEY, {});
        const hasKeys = (prefix: string) =>
          res.settings.some((s) => s.key.startsWith(`${prefix}.`) && s.configured);
        setChannels((prev) =>
          prev.map((c) => {
            const configured = hasKeys(c.id);
            const verified = configured && tests[c.id]?.ok === true;
            return { ...c, configured, verified, enabled: c.enabled && verified };
          }),
        );
      })
      .catch(() => {
        // Backend unreachable — keep cached `configured`, still require a passing test.
        if (cancelled) return;
        const tests = loadJson<Record<string, { ok: boolean }>>(TESTS_KEY, {});
        setChannels((prev) =>
          prev.map((c) => {
            const verified = c.configured && tests[c.id]?.ok === true;
            return { ...c, verified, enabled: c.enabled && verified };
          }),
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const persistChannels = useCallback((next: Channel[]) => {
    setChannels(next);
    window.localStorage.setItem(CHANNELS_KEY, JSON.stringify(next));
  }, []);

  const persistRules = useCallback((next: AlertRule[]) => {
    setRules(next);
    window.localStorage.setItem(RULES_KEY, JSON.stringify(next));
  }, []);

  const toggleChannel = (id: string) => {
    const ch = channels.find((c) => c.id === id);
    if (!ch) return;
    if (!ch.enabled && !ch.verified) {
      showToast(
        ch.configured
          ? `${ch.name} keys are saved but unverified — run Test in Data & Integrations first.`
          : `Add ${ch.name}'s keys in Data & Integrations before enabling it.`,
        "info",
      );
      return;
    }
    persistChannels(channels.map((c) => (c.id === id ? { ...c, enabled: !c.enabled } : c)));
  };

  const channelName = useMemo(() => Object.fromEntries(channels.map((c) => [c.id, c.name])), [channels]);

  const addRule = async () => {
    const name = draft.name.trim();
    if (!name) {
      showToast("Name the rule.");
      return;
    }
    const usableChannels = draft.channels.filter((id) => channels.find((c) => c.id === id)?.verified);
    if (!usableChannels.length) {
      showToast("Pick at least one verified channel — save and Test its keys in Data & Integrations first.", "info");
      return;
    }
    try {
      await createAlertRule({
        name,
        trigger: draft.trigger,
        threshold: draft.threshold ?? null,
        scope: draft.scope || "Any process",
        channels: usableChannels,
        enabled: draft.enabled,
      });
      await refreshRules();
      showToast(`Rule "${name}" created.`, "success");
    } catch {
      persistRules([{ ...draft, channels: usableChannels, name, id: `rule_${Date.now().toString(36)}` }, ...rules]);
      showToast(`Rule "${name}" saved offline.`, "info");
    }
    setDraft({ name: "", trigger: "grr_fail", scope: "Any gage", channels: ["slack"], enabled: true, threshold: undefined });
    setShowForm(false);
  };

  // Server records use UUIDs; offline records are prefixed "rule_".
  const removeRule = async (id: string) => {
    if (!id.startsWith("rule_")) {
      try {
        await deleteAlertRule(id);
        await refreshRules();
        return;
      } catch {
        showToast("Could not delete on the server; removed locally.", "info");
      }
    }
    persistRules(rules.filter((r) => r.id !== id));
  };

  const toggleRule = async (id: string) => {
    const rule = rules.find((r) => r.id === id);
    if (!rule) return;
    if (!id.startsWith("rule_")) {
      try {
        await updateAlertRule(id, { enabled: !rule.enabled });
        await refreshRules();
        return;
      } catch {
        showToast("Could not update on the server; changed locally.", "info");
      }
    }
    persistRules(rules.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)));
  };

  const loadSamples = async () => {
    try {
      await Promise.all(
        SAMPLE_RULES.map((r) =>
          createAlertRule({
            name: r.name,
            trigger: r.trigger,
            threshold: r.threshold ?? null,
            scope: r.scope,
            channels: r.channels,
            enabled: r.enabled,
          }),
        ),
      );
      await refreshRules();
      showToast("Example rules loaded.", "success");
    } catch {
      persistRules([...SAMPLE_RULES.map((r, i) => ({ ...r, id: `rule_seed_${Date.now().toString(36)}_${i}` })), ...rules]);
      showToast("Example rules loaded offline.", "info");
    }
  };

  const toggleDraftChannel = (id: string) => {
    setDraft((d) => ({ ...d, channels: d.channels.includes(id) ? d.channels.filter((c) => c !== id) : [...d.channels, id] }));
  };

  const activeRules = rules.filter((r) => r.enabled).length;
  const enabledChannels = channels.filter((c) => c.enabled).length;

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
                <Workflow size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="page-title md:text-[26px]">Alert Rules</h1>
                  <HelpTip text="Rules decide which alerts reach which people or channel. Example: send 'critical' SPC alerts to the night-shift Slack, and email everything else to the QA lead. You connect the channels themselves under Connections." />
                </div>
                <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                  Decide which alerts go to whom. Pick a channel you've connected, choose when it should fire, and you're done — no coding.
                </p>
              </div>
            </div>
            <button onClick={() => setShowForm((v) => !v)} className="btn btn-primary">
              <Plus size={16} /> New Rule
            </button>
          </div>
        </header>

        {/* Integration channels */}
        <section className="surface-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="section-label">Integration Channels</h2>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{enabledChannels} of {channels.length} enabled</span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {channels.map((c) => {
              const Icon = CHANNEL_ICON[c.kind];
              return (
                <div
                  key={c.id}
                  className="flex items-center gap-3 rounded-xl border p-3.5"
                  style={{
                    borderColor: c.enabled ? "var(--accent-bg-strong)" : "var(--border-default)",
                    background: c.enabled ? "var(--accent-bg)" : "var(--bg-surface)",
                  }}
                >
                  <div
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border"
                    style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)", color: c.enabled ? "var(--accent-bright)" : "var(--text-muted)" }}
                  >
                    <Icon size={16} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{c.name}</span>
                      {!c.configured ? (
                        <span className="badge badge-warning h-5 px-1.5 text-[9.5px]">Not configured</span>
                      ) : !c.verified ? (
                        <span className="badge badge-warning h-5 px-1.5 text-[9.5px]">Not verified</span>
                      ) : null}
                    </div>
                    <div className="truncate text-xs" style={{ color: "var(--text-muted)" }}>{c.detail}</div>
                  </div>
                  <button
                    onClick={() => toggleChannel(c.id)}
                    role="switch"
                    aria-checked={c.enabled}
                    title={!c.verified ? (c.configured ? "Run Test in Data & Integrations to enable" : "Add keys in Data & Integrations to enable") : c.enabled ? "Disable" : "Enable"}
                    className="relative h-[22px] w-[38px] shrink-0 rounded-full transition-colors"
                    style={{
                      background: c.enabled ? "var(--accent)" : "var(--bg-elevated)",
                      border: "1px solid var(--border-strong)",
                      opacity: c.verified ? 1 : 0.45,
                      cursor: c.verified ? "pointer" : "not-allowed",
                    }}
                  >
                    <span
                      className="absolute top-1/2 h-[16px] w-[16px] -translate-y-1/2 rounded-full bg-white transition-all"
                      style={{ left: c.enabled ? "18px" : "2px" }}
                    />
                  </button>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-[11px]" style={{ color: "var(--text-ghost)" }}>
            A channel is usable only after its keys are saved <em>and</em> pass a live{" "}
            <span style={{ color: "var(--text-secondary)" }}>Test</span> in{" "}
            <button
              type="button"
              onClick={() => setActivePage("integrations")}
              className="font-medium hover:underline"
              style={{ color: "var(--accent-bright)" }}
            >
              Data &amp; Integrations
            </button>
            {" "}— saving a wrong key leaves it &ldquo;not verified&rdquo;.
          </p>
        </section>

        {/* New rule form */}
        <AnimatePresence>
          {showForm && (
            <motion.section
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="surface-card p-5">
                <h2 className="section-label">New Alert Rule</h2>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Rule name</span>
                    <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className="input-field" placeholder="e.g. GR&R failure escalation" />
                  </label>
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Scope</span>
                    <input value={draft.scope} onChange={(e) => setDraft({ ...draft, scope: e.target.value })} className="input-field" placeholder="Any process / a specific gage name" />
                  </label>
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>When (trigger)</span>
                    <select value={draft.trigger} onChange={(e) => setDraft({ ...draft, trigger: e.target.value as TriggerId })} className="input-field">
                      {Object.entries(TRIGGERS).map(([id, label]) => (
                        <option key={id} value={id}>{label}</option>
                      ))}
                    </select>
                  </label>
                  {draft.trigger === "pass_rate_below" && (
                    <label className="block">
                      <span className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Pass-rate threshold (%)</span>
                      <input type="number" min={0} max={100} value={draft.threshold ?? ""} onChange={(e) => setDraft({ ...draft, threshold: e.target.value === "" ? undefined : Number(e.target.value) })} className="input-field stat-number" placeholder="e.g. 70" />
                    </label>
                  )}
                </div>

                <div className="mt-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Notify channels</span>
                    <button
                      type="button"
                      onClick={() => setActivePage("integrations")}
                      className="text-xs font-medium transition-colors hover:underline"
                      style={{ color: "var(--accent-bright)" }}
                    >
                      Manage integrations →
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {channels.filter((c) => NOTIFY_CHANNELS.includes(c.id)).map((c) => {
                      const picked = draft.channels.includes(c.id);
                      const Icon = CHANNEL_ICON[c.kind];
                      const usable = c.verified;
                      return (
                        <button
                          key={c.id}
                          onClick={() =>
                            usable
                              ? toggleDraftChannel(c.id)
                              : showToast(
                                  c.configured
                                    ? `${c.name} is saved but unverified — run Test in Data & Integrations first.`
                                    : `Configure ${c.name} in Data & Integrations first.`,
                                  "info",
                                )
                          }
                          title={
                            usable
                              ? undefined
                              : c.configured
                                ? `${c.name} keys saved but not verified — Test it in Data & Integrations`
                                : `${c.name} has no keys yet — set them up in Data & Integrations`
                          }
                          className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition"
                          style={{
                            borderColor: picked ? "var(--accent)" : "var(--border-default)",
                            background: picked ? "var(--accent-bg)" : "var(--bg-surface)",
                            color: usable ? (picked ? "var(--accent-bright)" : "var(--text-secondary)") : "var(--text-ghost)",
                            opacity: usable ? 1 : 0.5,
                            cursor: usable ? "pointer" : "not-allowed",
                          }}
                        >
                          <Icon size={13} /> {c.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="mt-5 flex items-center gap-2">
                  <button onClick={addRule} className="btn btn-primary h-9 px-4 text-sm"><Plus size={15} /> Create rule</button>
                  <button onClick={() => setShowForm(false)} className="btn btn-ghost h-9 px-4 text-sm">Cancel</button>
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Rules list */}
        <section className="surface-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="section-label">Routing Rules</h2>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{activeRules} active</span>
          </div>

          {rules.length === 0 ? (
            <div className="mt-4 flex min-h-[180px] flex-col items-center justify-center rounded-xl border border-dashed px-6 py-8 text-center" style={{ borderColor: "var(--border-default)", background: "var(--bg-root)" }}>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border" style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)", color: "var(--text-muted)" }}>
                <Zap size={18} />
              </div>
              <h3 className="mt-3 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>No rules yet</h3>
              <p className="mt-1 max-w-xs text-xs" style={{ color: "var(--text-muted)" }}>
                Define a rule to route quality events to your team automatically.
              </p>
              <div className="mt-4 flex items-center gap-2">
                <button onClick={() => setShowForm(true)} className="btn btn-primary h-9 px-4 text-sm"><Plus size={15} /> New rule</button>
                <button onClick={loadSamples} className="btn btn-secondary h-9 px-4 text-sm">Load examples</button>
              </div>
            </div>
          ) : (
            <div className="mt-4 space-y-2.5">
              {rules.map((rule) => (
                <motion.div
                  key={rule.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border p-4"
                  style={{ borderColor: "var(--border-default)", background: "var(--bg-surface)", opacity: rule.enabled ? 1 : 0.6 }}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{rule.name}</span>
                        <span className={`badge ${rule.enabled ? "badge-success" : "badge-info"} h-5 px-1.5 text-[9.5px]`}>
                          {rule.enabled ? "Active" : "Paused"}
                        </span>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
                        <span className="font-mono uppercase tracking-wider" style={{ color: "var(--text-ghost)" }}>when</span>
                        <span className="font-medium" style={{ color: "var(--text-primary)" }}>
                          {TRIGGERS[rule.trigger]}{rule.trigger === "pass_rate_below" && rule.threshold != null ? ` ${rule.threshold}%` : ""}
                        </span>
                        <span className="font-mono uppercase tracking-wider" style={{ color: "var(--text-ghost)" }}>on</span>
                        <span className="font-medium" style={{ color: "var(--text-primary)" }}>{rule.scope}</span>
                        <ArrowRight size={13} style={{ color: "var(--text-ghost)" }} />
                        <span className="flex flex-wrap gap-1">
                          {rule.channels.map((cid) => (
                            <span key={cid} className="badge badge-info h-5 px-1.5 text-[9.5px]">{channelName[cid] ?? cid}</span>
                          ))}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => toggleRule(rule.id)} className="btn-icon h-8 w-8" title={rule.enabled ? "Pause rule" : "Activate rule"}>
                        <Power size={14} style={{ color: rule.enabled ? "var(--success-text)" : "var(--text-muted)" }} />
                      </button>
                      <button onClick={() => removeRule(rule.id)} className="btn-icon h-8 w-8" title="Delete rule">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
