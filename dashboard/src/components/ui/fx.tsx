"use client";

/* Arad UI Kit — FX infrastructure: toasts, command palette, dropdown.
   TSX port of the prototype app/fx.jsx. */

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  CircleCheck,
  CircleX,
  TriangleAlert,
  Info,
  X,
  Search,
  Home,
  BarChart3,
  ClipboardCheck,
  Bell,
  Activity,
  Sparkles,
  ScrollText,
  Plus,
} from "lucide-react";

/* ───────────────────────── TOASTS ───────────────────────── */

export type ToastType = "success" | "error" | "warning" | "info";

interface ToastData {
  id: number;
  type: ToastType;
  title: string;
  msg?: string;
  duration: number;
  leaving?: boolean;
}

type ToastInput = { type?: ToastType; title: string; msg?: string; duration?: number };

const ToastStore = (() => {
  let toasts: ToastData[] = [];
  let subs: Array<(t: ToastData[]) => void> = [];
  let nextId = 1;
  const emit = () => subs.forEach((f) => f(toasts));
  return {
    subscribe(f: (t: ToastData[]) => void) {
      subs.push(f);
      return () => {
        subs = subs.filter((s) => s !== f);
      };
    },
    push(t: ToastInput) {
      const id = nextId++;
      toasts = [...toasts, { id, type: "info", duration: 4000, ...t }];
      emit();
      return id;
    },
    dismiss(id: number) {
      toasts = toasts.map((t) => (t.id === id ? { ...t, leaving: true } : t));
      emit();
      setTimeout(() => {
        toasts = toasts.filter((t) => t.id !== id);
        emit();
      }, 220);
    },
  };
})();

export function toast(t: ToastInput) {
  return ToastStore.push(t);
}

const TOAST_CONF: Record<ToastType, { c: string; Icon: typeof Info }> = {
  success: { c: "var(--success)", Icon: CircleCheck },
  error: { c: "var(--critical)", Icon: CircleX },
  warning: { c: "var(--warning)", Icon: TriangleAlert },
  info: { c: "var(--accent)", Icon: Info },
};

function ToastItem({ t }: { t: ToastData }) {
  const conf = TOAST_CONF[t.type] || TOAST_CONF.info;
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (t.leaving || !t.duration) return;
    const start = Date.now();
    const iv = setInterval(() => {
      const left = Math.max(0, 100 - ((Date.now() - start) / t.duration) * 100);
      setProgress(left);
      if (left <= 0) {
        clearInterval(iv);
        ToastStore.dismiss(t.id);
      }
    }, 30);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t.leaving]);

  return (
    <div
      style={{
        width: 340,
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-default)",
        borderLeft: `3px solid ${conf.c}`,
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-lg)",
        overflow: "hidden",
        animation: t.leaving ? "arad-toast-out .2s ease-in forwards" : "arad-toast-in .25s var(--ease-out)",
        pointerEvents: "auto",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "13px 14px" }}>
        <conf.Icon size={18} style={{ color: conf.c, marginTop: 1, flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{t.title}</div>
          {t.msg && (
            <div style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--text-secondary)", marginTop: 3, lineHeight: 1.45 }}>
              {t.msg}
            </div>
          )}
        </div>
        <button
          onClick={() => ToastStore.dismiss(t.id)}
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", display: "flex", padding: 2 }}
          aria-label="Dismiss notification"
        >
          <X size={14} />
        </button>
      </div>
      {t.duration ? (
        <div style={{ height: 2, background: "var(--border-default)" }}>
          <div style={{ height: "100%", width: `${progress}%`, background: conf.c, transition: "width .03s linear" }} />
        </div>
      ) : null}
    </div>
  );
}

export function ToastViewport() {
  const [toasts, setToasts] = useState<ToastData[]>([]);
  useEffect(() => {
    // Bridge: legacy showToast() calls (apiClient interceptor) route through this store.
    (window as unknown as { __aradToast?: (t: ToastInput) => void }).__aradToast = (t) => ToastStore.push(t);
    const unsub = ToastStore.subscribe(setToasts);
    return () => {
      delete (window as unknown as { __aradToast?: unknown }).__aradToast;
      unsub();
    };
  }, []);
  return (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        alignItems: "flex-end",
        pointerEvents: "none",
      }}
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} t={t} />
      ))}
    </div>
  );
}

/* ───────────────────────── DROPDOWN ───────────────────────── */

export interface DropdownItem {
  label?: string;
  icon?: ReactNode;
  kbd?: string;
  danger?: boolean;
  divider?: boolean;
  onClick?: () => void;
}

export function Dropdown({
  trigger,
  items,
  align = "left",
  width = 200,
}: {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: "left" | "right";
  width?: number;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);

  return (
    <span ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <span onClick={() => setOpen((o) => !o)}>{trigger}</span>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            [align]: 0,
            marginTop: 6,
            width,
            zIndex: 800,
            transformOrigin: "top",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-lg)",
            padding: 5,
            animation: "arad-dropdown-in .15s var(--ease-out)",
          }}
        >
          {items.map((it, i) =>
            it.divider ? (
              <div key={i} style={{ height: 1, background: "var(--border-default)", margin: "5px 0" }} />
            ) : (
              <button
                key={i}
                onClick={() => {
                  setOpen(false);
                  it.onClick?.();
                }}
                className="arad-dd-item"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 9,
                  width: "100%",
                  padding: "8px 9px",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  background: "transparent",
                  cursor: "pointer",
                  textAlign: "left",
                  fontFamily: "var(--font-sans)",
                  fontSize: 13,
                  color: it.danger ? "var(--critical-text)" : "var(--text-secondary)",
                  animation: `arad-menuitem-in .15s ${i * 20}ms var(--ease-out) both`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--bg-surface)";
                  e.currentTarget.style.color = it.danger ? "var(--critical-text)" : "var(--text-primary)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = it.danger ? "var(--critical-text)" : "var(--text-secondary)";
                }}
              >
                {it.icon}
                <span style={{ flex: 1 }}>{it.label}</span>
                {it.kbd && <kbd className="kbd">{it.kbd}</kbd>}
              </button>
            )
          )}
        </div>
      )}
    </span>
  );
}

/* ───────────────────────── COMMAND PALETTE (⌘K) ───────────────────────── */

interface Command {
  id: string;
  label: string;
  icon: typeof Home;
  kind: string;
  nav?: string;
  ask?: boolean;
}

const COMMANDS: Command[] = [
  { id: "dashboard", label: "Go to Dashboard", icon: Home, kind: "Navigate", nav: "dashboard" },
  { id: "grr", label: "Go to GR&R Studies", icon: BarChart3, kind: "Navigate", nav: "grr" },
  { id: "review", label: "Go to Review Queue", icon: ClipboardCheck, kind: "Navigate", nav: "review" },
  { id: "alerts", label: "Go to Alerts", icon: Bell, kind: "Navigate", nav: "alerts" },
  { id: "spc", label: "Go to SPC Monitor", icon: Activity, kind: "Navigate", nav: "spc" },
  { id: "assistant", label: "Go to AI Agent", icon: Sparkles, kind: "Navigate", nav: "agent" },
  { id: "audit", label: "Go to Audit Log", icon: ScrollText, kind: "Navigate", nav: "audit" },
  { id: "new-study", label: "New GR&R Study", icon: Plus, kind: "Action", nav: "grr" },
];

export function CommandPalette({
  open,
  onClose,
  onNavigate,
  onAsk,
}: {
  open: boolean;
  onClose: () => void;
  onNavigate: (page: string) => void;
  onAsk: (question: string) => void;
}) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const [debounced, setDebounced] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 150);
    return () => clearTimeout(t);
  }, [q]);

  const results = useMemo<Command[]>(() => {
    const s = debounced.trim().toLowerCase();
    if (!s) return COMMANDS.slice(0, 6);
    const matches = COMMANDS.filter((c) => c.label.toLowerCase().includes(s) || c.kind.toLowerCase().includes(s));
    // Anything typed can always be asked of the AI copilot.
    return [...matches, { id: "ask", label: `Ask AI: ${debounced.trim()}`, icon: Sparkles, kind: "Action", ask: true }];
  }, [debounced]);

  useEffect(() => {
    setActive(0);
  }, [results.length]);

  const choose = (c?: Command) => {
    if (!c) return;
    onClose();
    if (c.ask) onAsk(debounced.trim());
    else if (c.nav) onNavigate(c.nav);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  if (!open) return null;

  const kbdS: React.CSSProperties = {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-secondary)",
    border: "1px solid var(--border-strong)",
    borderRadius: 3,
    padding: "0 4px",
    minWidth: 16,
    textAlign: "center",
    display: "inline-block",
  };

  return (
    <div
      onMouseDown={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1500,
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        paddingTop: "14vh",
        background: "rgba(5,7,12,.6)",
        backdropFilter: "blur(8px)",
        animation: "arad-fade-in .15s ease-out",
      }}
    >
      <div
        onMouseDown={(e) => e.stopPropagation()}
        style={{
          width: 600,
          maxWidth: "92vw",
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-strong)",
          borderRadius: "var(--radius-xl)",
          boxShadow: "var(--shadow-lg)",
          overflow: "hidden",
          animation: "arad-modal-in .2s var(--ease-out)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 18px", borderBottom: "1px solid var(--border-default)" }}>
          <Search size={18} style={{ color: "var(--text-muted)" }} />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKey}
            placeholder="Search pages, actions — or ask the AI anything…"
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontFamily: "var(--font-sans)",
              fontSize: 15,
            }}
          />
          <kbd className="kbd">ESC</kbd>
        </div>
        <div style={{ maxHeight: 360, overflowY: "auto", padding: 8 }}>
          {results.map((c, i) => (
            <button
              key={c.id}
              onMouseEnter={() => setActive(i)}
              onClick={() => choose(c)}
              style={{
                position: "relative",
                display: "flex",
                alignItems: "center",
                gap: 12,
                width: "100%",
                padding: "11px 12px",
                border: "none",
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                textAlign: "left",
                background: "transparent",
                overflow: "hidden",
                animation: `arad-menuitem-in .18s ${i * 30}ms var(--ease-out) both`,
              }}
            >
              {active === i && (
                <span
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: "var(--accent-bg)",
                    animation: "arad-grow-x .1s var(--ease-out)",
                    transformOrigin: "left",
                    borderRadius: "var(--radius-md)",
                  }}
                />
              )}
              <c.icon size={17} style={{ position: "relative", color: active === i ? "var(--accent)" : "var(--text-muted)", flexShrink: 0 }} />
              <span
                style={{
                  position: "relative",
                  flex: 1,
                  fontFamily: "var(--font-sans)",
                  fontSize: 14,
                  color: active === i ? "var(--text-primary)" : "var(--text-secondary)",
                }}
              >
                {c.label}
              </span>
              <span
                style={{
                  position: "relative",
                  fontFamily: "var(--font-sans)",
                  fontSize: 10,
                  fontWeight: 600,
                  letterSpacing: ".06em",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  border: "1px solid var(--border-default)",
                  borderRadius: 4,
                  padding: "2px 6px",
                }}
              >
                {c.kind}
              </span>
            </button>
          ))}
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "9px 16px",
            borderTop: "1px solid var(--border-default)",
            fontFamily: "var(--font-sans)",
            fontSize: 11,
            color: "var(--text-muted)",
          }}
        >
          <span style={{ display: "inline-flex", gap: 5, alignItems: "center" }}>
            <kbd style={kbdS}>↑</kbd>
            <kbd style={kbdS}>↓</kbd> navigate
          </span>
          <span style={{ display: "inline-flex", gap: 5, alignItems: "center" }}>
            <kbd style={kbdS}>↵</kbd> select
          </span>
        </div>
      </div>
    </div>
  );
}
