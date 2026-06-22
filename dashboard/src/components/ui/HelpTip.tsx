"use client";

import { useState } from "react";
import { HelpCircle } from "lucide-react";

/**
 * A small "?" affordance that explains a page or term in plain language.
 * Hover or focus (keyboard) to reveal — kept deliberately simple so a
 * non-technical user always has a one-tap "what is this?" within reach.
 */
export default function HelpTip({ text, label = "What's this?" }: { text: string; label?: string }) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex align-middle">
      <button
        type="button"
        aria-label={label}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
        className="flex h-5 w-5 items-center justify-center rounded-full border transition-colors"
        style={{
          borderColor: "var(--border-default)",
          background: "var(--bg-elevated)",
          color: open ? "var(--accent-bright)" : "var(--text-muted)",
        }}
      >
        <HelpCircle size={12} />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute left-1/2 top-[calc(100%+8px)] z-40 w-64 max-w-[70vw] -translate-x-1/2 rounded-lg border px-3 py-2.5 text-xs font-normal leading-relaxed"
          style={{
            borderColor: "var(--border-default)",
            background: "var(--bg-surface)",
            color: "var(--text-secondary)",
            boxShadow: "var(--shadow-lg)",
          }}
        >
          {text}
        </span>
      )}
    </span>
  );
}
