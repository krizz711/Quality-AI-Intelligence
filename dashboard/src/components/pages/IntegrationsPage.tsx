"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Plug,
  MessageSquare,
  Mail,
  Smartphone,
  Ticket,
  Database,
  Sparkles,
  Save,
  Loader2,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  DownloadCloud,
  UploadCloud,
  Bell,
  Wrench,
  FileSpreadsheet,
  Trash2,
} from "lucide-react";
import {
  getSettings,
  updateSettings,
  testIntegration,
  clearIntegration,
  uploadMeasurements,
  showToast,
  type UploadResult,
} from "@/api/apiClient";

type Field = { key: string; label: string; secret?: boolean; placeholder?: string; type?: string };
type Group = {
  id: string;
  title: string;
  detail: string;
  // "alerts" = a quality engineer chooses where notifications go.
  // "advanced" = a one-time technical hookup, usually done by IT.
  audience: "alerts" | "advanced";
  icon: React.ComponentType<{ size?: number; className?: string }>;
  fields: Field[];
};

const GROUPS: Group[] = [
  {
    id: "slack",
    title: "Slack",
    detail: "Post quality alerts to a Slack channel your team watches",
    audience: "alerts",
    icon: MessageSquare,
    fields: [{ key: "slack.webhook_url", label: "Slack webhook link", secret: true, placeholder: "https://hooks.slack.com/services/…" }],
  },
  {
    id: "email",
    title: "Email",
    detail: "Email your team when an alert needs a closer look",
    audience: "alerts",
    icon: Mail,
    fields: [
      { key: "email.smtp_host", label: "Mail server (SMTP host)", placeholder: "smtp.gmail.com" },
      { key: "email.smtp_port", label: "Port", placeholder: "587", type: "number" },
      { key: "email.smtp_user", label: "Username", placeholder: "alerts@company.com" },
      { key: "email.smtp_password", label: "Password", secret: true },
      { key: "email.from_address", label: "Send from address", placeholder: "quality@company.com" },
      { key: "email.recipients", label: "Send to (separate emails with commas)", placeholder: "qa-lead@company.com, supervisor@company.com" },
    ],
  },
  {
    id: "sms",
    title: "Text message",
    detail: "Text a few people for critical alerts that can't wait",
    audience: "alerts",
    icon: Smartphone,
    fields: [
      { key: "sms.webhook_url", label: "Twilio API URL", placeholder: "https://api.twilio.com/2010-04-01/Accounts/…/Messages.json" },
      { key: "sms.auth_token", label: "Auth token", secret: true },
      { key: "sms.from_number", label: "Send from number", placeholder: "+15550000000" },
      { key: "sms.to_numbers", label: "Send to numbers (separate with commas)", placeholder: "+15551111111, +15552222222" },
    ],
  },
  {
    id: "jira",
    title: "JIRA",
    detail: "Automatically open a ticket when a study fails or a problem keeps repeating",
    audience: "advanced",
    icon: Ticket,
    fields: [
      { key: "jira.url", label: "JIRA address", placeholder: "https://company.atlassian.net" },
      { key: "jira.email", label: "Account email", placeholder: "automation@company.com" },
      { key: "jira.api_token", label: "API token", secret: true },
      { key: "jira.project_key", label: "Project key", placeholder: "QUAL" },
    ],
  },
  {
    id: "qms",
    title: "QMS",
    detail: "Send quality events to your quality management system",
    audience: "advanced",
    icon: Database,
    fields: [{ key: "qms.api_url", label: "QMS events URL", placeholder: "https://qms.company.com/api/events" }],
  },
  {
    id: "mes",
    title: "Automatic data feed (MES / QMS)",
    detail: "Pull measurements from your machine or MES system on a schedule — no manual uploads needed",
    audience: "advanced",
    icon: DownloadCloud,
    fields: [
      { key: "mes.api_url", label: "Measurements API URL", placeholder: "https://mes.company.com/api/v1/measurements" },
      { key: "mes.api_token", label: "API token (Bearer)", secret: true },
      { key: "mes.field_map", label: "Field map (JSON: our field → their column)", placeholder: '{"timestamp":"measuredAt","part_number":"partNo","measured_value":"value"}' },
      { key: "mes.records_path", label: "Records path in response (optional)", placeholder: "data" },
      { key: "mes.since_param", label: "Incremental query param (optional)", placeholder: "since" },
      { key: "mes.id_field", label: "Record id field for dedup (optional)", placeholder: "id" },
      { key: "mes.poll_interval_seconds", label: "How often to check (seconds)", type: "number", placeholder: "60" },
    ],
  },
  {
    id: "llm",
    title: "AI summaries",
    detail: "Plain-English write-ups on your GR&R results and alerts — pick a provider and paste its key",
    audience: "advanced",
    icon: Sparkles,
    fields: [
      { key: "llm.provider", label: "AI provider" },
      { key: "llm.gemini_api_key", label: "Gemini API key", secret: true, placeholder: "AIza…" },
      { key: "llm.anthropic_api_key", label: "Claude API key", secret: true, placeholder: "sk-ant-…" },
      { key: "llm.openai_api_key", label: "OpenAI API key", secret: true, placeholder: "sk-…" },
    ],
  },
];

// AI-summary providers shown as a radio in the "AI summaries" card. Each maps to
// its own stored secret key so switching providers never loses the other keys.
const LLM_PROVIDERS = [
  { id: "gemini", label: "Gemini", keyField: "llm.gemini_api_key", placeholder: "AIza…", hint: "Free key at aistudio.google.com/apikey" },
  { id: "claude", label: "Claude", keyField: "llm.anthropic_api_key", placeholder: "sk-ant-…", hint: "Key at console.anthropic.com" },
  { id: "openai", label: "OpenAI", keyField: "llm.openai_api_key", placeholder: "sk-…", hint: "Key at platform.openai.com/api-keys" },
];

// Editing a provider's key clears only that provider's verification (key → provider).
const LLM_KEY_PROVIDER: Record<string, string> = {
  "llm.gemini_api_key": "gemini",
  "llm.anthropic_api_key": "claude",
  "llm.openai_api_key": "openai",
};

// Live test results are persisted so a verified channel stays verified across
// reloads — editing any of a group's fields clears it (the saved value changed,
// so the old pass/fail no longer applies). Shared with Alert Rules via this key.
const TESTS_KEY = "arad-integration-tests";
type TestResult = { ok: boolean; message: string };

function loadTests(): Record<string, TestResult> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(window.localStorage.getItem(TESTS_KEY) || "{}") as Record<string, TestResult>;
  } catch {
    return {};
  }
}

function saveTests(next: Record<string, TestResult>) {
  try {
    window.localStorage.setItem(TESTS_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable — verification falls back to session-only */
  }
}

export default function IntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [configured, setConfigured] = useState<Record<string, boolean>>({});
  const [tested, setTested] = useState<Record<string, { ok: boolean; message: string }>>({});
  const [testing, setTesting] = useState<string | null>(null);
  const [clearing, setClearing] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  const load = useCallback(async () => {
    setTested(loadTests());
    setLoading(true);
    try {
      const res = await getSettings();
      const f: Record<string, string> = {};
      const c: Record<string, boolean> = {};
      for (const s of res.settings) {
        c[s.key] = s.configured;
        f[s.key] = s.secret ? "" : s.value ?? "";
      }
      setForm(f);
      setConfigured(c);
      // Server-side test results are the source of truth; mirror to cache.
      if (res.tests) {
        setTested(res.tests);
        saveTests(res.tests);
      }
    } catch {
      showToast("Could not load settings — is the backend reachable?", "info");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const llmProvider = () => form["llm.provider"] || "gemini";
  const testKeyForId = (id: string) => (id === "llm" ? `llm:${llmProvider()}` : id);

  const setField = (key: string, value: string) => {
    setForm((p) => ({ ...p, [key]: value }));
    // Editing a key invalidates any prior pass/fail for that integration. The "llm"
    // group is per-provider: switching the provider radio keeps every provider's
    // verification; editing a provider's key clears only that provider's result.
    const groupId = key.split(".")[0];
    let testKey: string | null = groupId;
    if (groupId === "llm") {
      testKey = key === "llm.provider" ? null : `llm:${LLM_KEY_PROVIDER[key] ?? llmProvider()}`;
    }
    if (!testKey) return;
    const target = testKey;
    setTested((p) => {
      if (!(target in p)) return p;
      const next = { ...p };
      delete next[target];
      saveTests(next);
      return next;
    });
  };

  const save = async () => {
    // Non-secret values are always sent; secrets only when the user typed one.
    const payload: Record<string, string> = {};
    for (const g of GROUPS) {
      for (const fld of g.fields) {
        const v = form[fld.key] ?? "";
        if (fld.secret) {
          if (v.trim()) payload[fld.key] = v;
        } else {
          payload[fld.key] = v;
        }
      }
    }
    setSaving(true);
    try {
      const res = await updateSettings(payload);
      const c: Record<string, boolean> = {};
      for (const s of res.settings) c[s.key] = s.configured;
      setConfigured(c);
      // Clear typed secrets now that they're stored.
      setForm((p) => {
        const n = { ...p };
        for (const g of GROUPS) for (const fld of g.fields) if (fld.secret) n[fld.key] = "";
        return n;
      });
      showToast("Saved. Your changes take effect right away.", "success");
    } catch {
      showToast("Save failed — check your connection and permissions.", "info");
    } finally {
      setSaving(false);
    }
  };

  const runTest = async (groupId: string) => {
    setTesting(groupId);
    try {
      // Save first so the test runs against what the user just typed — otherwise an
      // unsaved webhook/token reads as "not configured" and the test fails confusingly.
      await save();
      const res = await testIntegration(groupId);
      const tkey = testKeyForId(groupId);
      setTested((p) => { const next = { ...p, [tkey]: res }; saveTests(next); return next; });
    } catch {
      const tkey = testKeyForId(groupId);
      setTested((p) => { const next = { ...p, [tkey]: { ok: false, message: "Test request failed." } }; saveTests(next); return next; });
    } finally {
      setTesting(null);
    }
  };

  const clearGroup = async (g: Group) => {
    if (!window.confirm(`Remove all saved ${g.title} credentials? You'll need to enter them again to use it.`)) return;
    setClearing(g.id);
    try {
      const res = await clearIntegration(g.id);
      const c: Record<string, boolean> = {};
      for (const s of res.settings) c[s.key] = s.configured;
      setConfigured(c);
      // Blank the form fields for this group and drop its verification.
      setForm((p) => {
        const n = { ...p };
        for (const fld of g.fields) n[fld.key] = "";
        return n;
      });
      setTested((p) => {
        const next = { ...p };
        if (g.id === "llm") {
          for (const k of Object.keys(next)) if (k === "llm" || k.startsWith("llm:")) delete next[k];
        } else {
          delete next[g.id];
        }
        saveTests(next);
        return next;
      });
      showToast(`${g.title} credentials removed.`, "success");
    } catch {
      showToast("Could not remove credentials — check your connection.", "info");
    } finally {
      setClearing(null);
    }
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const res = await uploadMeasurements(file);
      setUploadResult(res);
      const parts = [`Added ${res.ingested} new measurement${res.ingested === 1 ? "" : "s"}`];
      if (res.duplicates) parts.push(`${res.duplicates} already on file`);
      if (res.skipped) parts.push(`${res.skipped} skipped`);
      showToast(parts.join(" · ") + ".", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Upload failed", "error");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const groupConfigured = (g: Group) => g.fields.some((f) => f.key !== "llm.provider" && configured[f.key]);

  const renderGroup = (g: Group) => {
    const Icon = g.icon;
    const isConfigured = groupConfigured(g);
    const result = tested[testKeyForId(g.id)];
    const status = !isConfigured ? "not_set" : result?.ok ? "verified" : result ? "failing" : "untested";
    const statusBadge = {
      not_set: { cls: "badge-info", text: "Not set up" },
      untested: { cls: "badge-warning", text: "Saved · not tested" },
      verified: { cls: "badge-success", text: "Working" },
      failing: { cls: "badge-critical", text: "Test failed" },
    }[status];
    return (
      <motion.section key={g.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className="flex h-9 w-9 items-center justify-center rounded-lg border"
              style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)", color: isConfigured ? "var(--accent-bright)" : "var(--text-muted)" }}
            >
              <Icon size={16} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{g.title}</h2>
                <span className={`badge ${statusBadge.cls} h-5 px-1.5 text-[9.5px]`}>
                  {statusBadge.text}
                </span>
              </div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>{g.detail}</div>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            {result && (
              <span
                className="inline-flex items-center gap-1.5 text-xs"
                style={{ color: result.ok ? "var(--success-text)" : "var(--critical-text)" }}
              >
                {result.ok ? <CheckCircle2 size={13} /> : <XCircle size={13} />} {result.message}
              </span>
            )}
            <button onClick={() => void runTest(g.id)} disabled={testing === g.id || clearing === g.id} className="btn btn-secondary h-8 px-3 text-xs" title="Send a test to make sure it works">
              {testing === g.id ? <Loader2 size={13} className="animate-spin" /> : null} Send test
            </button>
            {isConfigured && (
              <button
                onClick={() => void clearGroup(g)}
                disabled={clearing === g.id || testing === g.id}
                className="btn btn-secondary h-8 px-3 text-xs"
                title="Remove the saved credentials for this connection"
                style={{ color: "var(--critical-text)" }}
              >
                {clearing === g.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />} Remove
              </button>
            )}
          </div>
        </div>
        {g.id === "llm" ? (
          <div className="mt-4 space-y-3">
            <div>
              <span className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>AI provider</span>
              <div className="flex flex-wrap gap-2">
                {LLM_PROVIDERS.map((p) => {
                  const active = (form["llm.provider"] || "gemini") === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setField("llm.provider", p.id)}
                      className="btn btn-secondary h-8 px-3 text-xs"
                      style={active ? { borderColor: "var(--accent-bright)", color: "var(--accent-bright)" } : undefined}
                    >
                      {active ? "● " : "○ "}{p.label}{p.id === "gemini" ? " (default)" : ""}
                    </button>
                  );
                })}
              </div>
            </div>
            {(() => {
              const provider = form["llm.provider"] || "gemini";
              const meta = LLM_PROVIDERS.find((p) => p.id === provider) ?? LLM_PROVIDERS[0];
              return (
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>{meta.label} API key</span>
                  <input
                    value={form[meta.keyField] ?? ""}
                    onChange={(e) => setField(meta.keyField, e.target.value)}
                    type="password"
                    autoComplete="off"
                    spellCheck={false}
                    className="input-field"
                    placeholder={configured[meta.keyField] ? "•••••••• (saved — leave blank to keep)" : meta.placeholder}
                  />
                  <span className="mt-1.5 block text-[11px]" style={{ color: "var(--text-muted)" }}>{meta.hint}</span>
                </label>
              );
            })()}
          </div>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {g.fields.map((fld) => (
              <label key={fld.key} className="block">
                <span className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>{fld.label}</span>
                <input
                  value={form[fld.key] ?? ""}
                  onChange={(e) => setField(fld.key, e.target.value)}
                  type={fld.secret ? "password" : fld.type ?? "text"}
                  autoComplete="off"
                  spellCheck={false}
                  className="input-field"
                  placeholder={fld.secret && configured[fld.key] ? "•••••••• (saved — leave blank to keep)" : fld.placeholder ?? ""}
                />
              </label>
            ))}
          </div>
        )}
      </motion.section>
    );
  };

  const alertGroups = GROUPS.filter((g) => g.audience === "alerts");
  const advancedGroups = GROUPS.filter((g) => g.audience === "advanced");

  return (
    <div className="h-full overflow-y-auto px-4 py-6 md:px-6" style={{ color: "var(--text-primary)" }}>
      <div className="mx-auto flex max-w-5xl flex-col gap-5">
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
                <Plug size={20} />
              </div>
              <div>
                <h1 className="page-title md:text-[26px]">Connections</h1>
                <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                  Two things live here: <span style={{ color: "var(--text-primary)" }}>where your quality alerts go</span> (Slack, email, text)
                  and <span style={{ color: "var(--text-primary)" }}>how your measurement data gets in</span>. Fill in only what you use — you can always come back.
                </p>
              </div>
            </div>
            <button onClick={() => void save()} disabled={saving || loading} className="btn btn-primary">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save changes
            </button>
          </div>
          <div className="mt-4 flex items-center gap-2 panel-inset px-4 py-2.5 text-xs" style={{ color: "var(--text-muted)" }}>
            <ShieldCheck size={14} style={{ color: "var(--success)" }} />
            Anything you type here is encrypted on your own server and never shown again after saving. Use <strong>Send test</strong> to confirm it works.
          </div>
        </header>

        {/* Upload — the simplest way for an engineer to get data in */}
        <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div
                className="flex h-9 w-9 items-center justify-center rounded-lg border"
                style={{ borderColor: "var(--border-default)", background: "var(--bg-elevated)", color: "var(--accent-bright)" }}
              >
                <FileSpreadsheet size={16} />
              </div>
              <div>
                <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Upload a spreadsheet (CSV or Excel)</h2>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                  The easiest way to add data. Export from any machine, gauge, or lab system and drop it in — we figure out the columns and start watching the new data automatically.
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              {uploadResult && (
                <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: "var(--success-text)" }}>
                  <CheckCircle2 size={13} /> Added {uploadResult.ingested} new
                  {uploadResult.duplicates ? `, ${uploadResult.duplicates} already on file` : ""}
                  {uploadResult.skipped ? `, ${uploadResult.skipped} skipped` : ""}
                </span>
              )}
              <label className="btn btn-secondary h-8 px-3 text-xs cursor-pointer">
                <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={(e) => void onUpload(e)} disabled={uploading} />
                {uploading ? <Loader2 size={13} className="animate-spin" /> : <UploadCloud size={13} />} Choose file
              </label>
            </div>
          </div>
        </motion.section>

        {loading ? (
          <div className="surface-card flex items-center justify-center gap-2 p-10 text-sm" style={{ color: "var(--text-muted)" }}>
            <Loader2 size={18} className="animate-spin" /> Loading your settings…
          </div>
        ) : (
          <>
            {/* Section 1 — quality-engineer-facing: where alerts go */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2.5 px-1">
                <Bell size={15} style={{ color: "var(--accent-bright)" }} />
                <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Where should alerts go?</h2>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>Turn on any your team uses</span>
              </div>
              <div className="grid gap-4">{alertGroups.map(renderGroup)}</div>
            </div>

            {/* Section 2 — IT-facing: one-time technical hookups */}
            <div className="mt-2 flex flex-col gap-3">
              <div className="flex items-center gap-2.5 px-1">
                <Wrench size={15} style={{ color: "var(--text-muted)" }} />
                <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Advanced connections</h2>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>Usually set up once by IT or our support team</span>
              </div>
              <div className="grid gap-4">{advancedGroups.map(renderGroup)}</div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
