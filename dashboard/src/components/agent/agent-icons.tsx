"use client";

import type { SVGProps } from "react";

/**
 * Custom glyph set for the agent activity log — one shared instrument language:
 * 24×24 grid, 1.7 stroke, round caps/joins, currentColor. Hand-built so the
 * agent's "thinking" steps read as precision tooling, not generic UI icons.
 */
type GlyphProps = SVGProps<SVGSVGElement> & { size?: number };

function Glyph({ size = 18, children, ...rest }: GlyphProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Parse intent — language brackets tokenizing into nodes. */
export const GlyphParse = (p: GlyphProps) => (
  <Glyph {...p}>
    <path d="M8.5 5H6a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h2.5" />
    <path d="M15.5 5H18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2.5" />
    <circle cx="9.4" cy="12" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="12" cy="12" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="14.6" cy="12" r="0.9" fill="currentColor" stroke="none" />
  </Glyph>
);

/** GR&R studies — a dial gauge (measurement-system capability). */
export const GlyphGauge = (p: GlyphProps) => (
  <Glyph {...p}>
    <circle cx="12" cy="13.5" r="6.3" />
    <path d="M12 13.5l3.2-3.2" />
    <circle cx="12" cy="13.5" r="1" fill="currentColor" stroke="none" />
    <path d="M10 4.6h4" />
    <path d="M12 4.6v2.6" />
  </Glyph>
);

/** SPC violations — control chart with a point breaching the upper limit. */
export const GlyphControlChart = (p: GlyphProps) => (
  <Glyph {...p}>
    <path d="M5 5v14h14" />
    <path d="M5 9h14" strokeDasharray="2 2.2" strokeWidth="1.3" />
    <path d="M5 16.5l3-1.8 2.7 1L14 8l3 3.4" />
    <circle cx="14" cy="8" r="1.5" fill="currentColor" stroke="none" />
  </Glyph>
);

/** Review queue — clipboard with a sign-off check. */
export const GlyphReview = (p: GlyphProps) => (
  <Glyph {...p}>
    <path d="M8 5H7a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-1" />
    <path d="M9 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1H9z" />
    <path d="M9 13.2l2 2 4-4.2" />
  </Glyph>
);

/** Reasoning — a faceted processing core that echoes the Agent Core mark. */
export const GlyphReason = (p: GlyphProps) => (
  <Glyph {...p}>
    <path d="M12 3.6l7.3 4.2v8.4L12 20.4 4.7 16.2V7.8z" />
    <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <path d="M12 12l5-2.9M12 12l-5-2.9M12 12v5" strokeWidth="1.3" />
  </Glyph>
);

/** Compose — a nib drawing the answer onto a baseline. */
export const GlyphCompose = (p: GlyphProps) => (
  <Glyph {...p}>
    <path d="M14.6 5.8l3.1 3.1" />
    <path d="M6 18.4l1.4-4.2 7.7-7.7 3.1 3.1-7.7 7.7z" />
    <path d="M5 21h7" />
  </Glyph>
);

/** Source/database — context the agent pulled into the prompt. */
export const GlyphSource = (p: GlyphProps) => (
  <Glyph {...p}>
    <path d="M5 6.6c0-1.6 3.1-2.8 7-2.8s7 1.2 7 2.8-3.1 2.8-7 2.8-7-1.2-7-2.8z" />
    <path d="M5 6.6v10.8c0 1.6 3.1 2.8 7 2.8s7-1.2 7-2.8V6.6" />
    <path d="M5 12c0 1.6 3.1 2.8 7 2.8s7-1.2 7-2.8" />
  </Glyph>
);

/** Completion check. */
export const GlyphCheck = (p: GlyphProps) => (
  <Glyph {...p}>
    <path d="M4.5 12.5l4.5 4.5L19.5 6.5" />
  </Glyph>
);

export const STEP_GLYPHS = {
  parse: GlyphParse,
  grr: GlyphGauge,
  spc: GlyphControlChart,
  review: GlyphReview,
  reason: GlyphReason,
  compose: GlyphCompose,
} as const;
