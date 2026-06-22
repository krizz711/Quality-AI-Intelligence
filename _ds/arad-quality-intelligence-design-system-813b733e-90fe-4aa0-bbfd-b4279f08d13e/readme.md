# Arad Quality Intelligence — Design System

> **Precision at every measurement.**
> The design system for Arad Quality Intelligence, a premium ($10K/yr) B2B SaaS
> platform for manufacturing quality control — built for shop-floor engineers and
> quality managers. Dark industrial-tech: aerospace control room meets Silicon Valley SaaS.

This project is the **source of truth** for Arad's brand, tokens, components and product
UI. An automated compiler bundles the React components into a runtime library
(`window.AradQualityIntelligenceDesignSystem_813b73`) and indexes the CSS tokens. Consumers link a
single file: **`styles.css`**.

---

## Product context

Arad helps quality teams run and interpret **Gauge R&R (GR&R)** measurement-system-analysis
studies, monitor live **SPC (Statistical Process Control)** charts, triage AI-detected
**alerts** against Nelson rules, work a **review/approval queue**, and ask an **AI assistant**
about their quality data. The product is data-dense, real-time, and compliance-aware
(SOC 2, full audit trail).

**Surfaces (one product, web app):**
1. **Dashboard** — live SPC overview, KPI strip, activity feed, accuracy gauge, AI spend.
2. **GR&R Studies** — submit studies (multi-step form), view AI-narrated results, history.
3. **Review Queue** — table of pending approvals + right-side decision drawer.
4. **Alerts** — severity-coded alert feed + accuracy tracker.
5. **AI Assistant** — full-page chat with system-context sidebar.

**Sources:** This system was authored from a detailed written design brief (no codebase or
Figma was attached). All values — palette, type scale, layout dims, component states — come
from that brief. If a codebase or Figma later exists, reconcile against it and update tokens.

---

## CONTENT FUNDAMENTALS

**Voice:** Precise, confident, engineering-literate. Speaks the language of metrology
(%GR&R, NDC, EV/AV/PV, UCL/LCL, Nelson rules) without over-explaining. Never breezy or
cute — this is a tool trusted with $10K/yr quality decisions.

**Person & address:** System-neutral and declarative for data ("3 critical", "Bore Diameter
exceeded UCL"). Direct address ("you") only in empty states and guidance ("Submit your first
study to see results here"). AI assistant speaks in first-person-light, structured prose.

**Casing:**
- **ALL-CAPS + letter-spacing (0.08em)** for micro-labels: table headers, KPI labels, field
  labels, badge text. 11px.
- **Sentence case** for body copy, descriptions, AI narratives, buttons ("Run Analysis",
  "Download PDF Report").
- **Title Case** for page/section headings ("Live Process Monitor", "Review Queue").

**Numbers:** Every metric, measurement, percentage, ID, timestamp, and limit renders in
**monospace (JetBrains Mono)**. This is the single most important content rule — numbers must
look engineered. Examples: `97.3%`, `PN-4821`, `CMM-001`, `10.042`, `NDC 4`, `1.2 hrs`.

**Status language:** Verdicts are terse and symbol-prefixed — `✓ Acceptable`,
`⚠ Requires Review`, `✗ Not Acceptable`. Severities are single uppercase words —
`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.

**Emoji:** None in product chrome. The only glyphs used are the verdict marks (✓ ⚠ ✗), the
delta triangles (▲ ▼) on KPI deltas, and the sparkle on AI attributions. No decorative emoji.

**Enterprise trust copy:** Every page footer carries the same line:
*"All data encrypted in transit · SOC 2 Type II · Full audit trail."*

**Example strings:**
- KPI subtitle (good): `+12 this week` · `▲ vs 95% SLA` · `✓ under 2hr SLA`
- Alert: `Bore Diameter exceeded UCL: 10.042 vs UCL 10.030`
- Summary chip: `3 operators × 10 parts × 2 trials = 60 measurements`
- AI attribution: `Powered by Gemini` (very small, muted)

---

## VISUAL FOUNDATIONS

**Mood:** Dark-only, near-black, high-contrast, data-rich but never cluttered. Confident
negative space around dense data. No light mode.

**Color:** Near-black background (`#0A0B0F`) — never pure black. Three surface tiers
(`#111318` card → `#181C24` elevated → `#0D1017` inset/inputs). Electric blue (`#3B82F6`) is
the precision/primary accent; indigo (`#6366F1`) is reserved for **AI/intelligence**.
Semantic trio: emerald pass, amber conditional, red fail. Status badges use deep-tinted
backgrounds with bright text (e.g. pass `#022C22` bg / `#34D399` text). See `tokens/colors.css`.

**Type:** Inter for display & body (600–700 headings, 400–500 body); **JetBrains Mono for all
data**. Scale: 11 caption → 13 body → 15 subhead → 20 heading → 32 display (28 for KPI numbers).
Caps labels carry 0.08em tracking. *(Substitution: brief allowed "Inter or Geist"; we ship
Inter via Google Fonts. Provide Geist binaries to self-host if preferred — see CAVEATS.)*

**Spacing & radii:** 4px base scale. Radii: 4 (badges/pills) · 6 (buttons/inputs) · 10 (cards)
· 14 (drawers). Buttons 36px tall, inputs 40px.

**Elevation:** Shadows are **blue-tinted, never grey** — a hairline ring + soft drop:
`0 0 0 1px rgba(59,130,246,.08), 0 4px 24px rgba(0,0,10,.4)`. Interactive cards gain a blue
**glow** on hover (`0 0 0 1px rgba(59,130,246,.35), 0 0 20px rgba(59,130,246,.12)`).

**Backgrounds:** No imagery or illustration photography. Very subtle gradient-mesh accents
(~5% opacity) are permitted on hero/empty areas. No repeating textures, no noise/grain.

**Borders:** 1px `#1E2330` hairlines everywhere. Tables use **row separators only** — no outer
border. The signature AI treatment is a **3px indigo left border** on a card.

**Animation:** All transitions **150ms ease-out** (`cubic-bezier(.16,1,.3,1)`). Real-time
elements are never static — status dots have an **expanding pulse ring**; numbers **count up**
when they update; charts draw in; loading uses **skeleton + shimmer sweep**. No bounce, no
playful overshoot, no infinite decorative loops on content.

**Hover states:** Buttons brighten (primary) or gain a blue glow (secondary); ghost gains a
surface bg. Table rows shift to `#161B26`. Cards glow blue.

**Press states:** Subtle — rely on color shift, not large scale changes.

**Cards:** `#111318` surface, 1px `#1E2330` border, 10px radius, blue-tinted shadow. AI cards
add a 3px indigo left border + sparkle. KPI cards are 110px min-height with a corner sparkline.

**Charts:** Dark bg, no/very-subtle grid. Axis labels monospace 11px muted. Data line solid
white 1.5px. UCL/LCL dashed red tint; CL dashed blue tint. Violation points red fill + pulse
ring. Area fill is a blue gradient (line→baseline, ~6–16% opacity). Tooltips are elevated dark
cards with a blue border, all values monospace.

**Transparency/blur:** Used sparingly — drawer/modal scrims, and the subtle gradient-mesh.

---

## ICONOGRAPHY

**System:** [Lucide](https://lucide.dev) icons, loaded from CDN (`lucide@latest`). Lucide's
1.5–2px stroke, rounded-join line style matches the precise, technical aesthetic. *(No icon
font or SVG sprite was provided in the brief; Lucide is the chosen substitute — flag for
replacement if Arad has a proprietary set.)*

**Usage:**
- **Stroke icons only**, never filled, at 16–20px in chrome; stroke inherits `currentColor`.
- Nav icons: `home`, `bar-chart-3`, `clipboard-check`, `bell`, `trending-up`, `sparkles`,
  `shield`, `settings`.
- The **Arad logo** is a geometric **hexagon** mark + wordmark (see `assets/`).
- **Glyph characters** (not icon font) used as status marks: `✓ ⚠ ✗ ▲ ▼`. The AI sparkle is
  the Lucide `sparkles` icon, tinted indigo.
- **No emoji** anywhere in product chrome.

---

## INDEX / MANIFEST

**Root**
- `styles.css` — global entry (imports only). Consumers link this.
- `readme.md` — this guide.
- `SKILL.md` — portable Agent-Skill wrapper.

**`tokens/`** — `fonts.css`, `colors.css`, `typography.css`, `spacing.css`, `elevation.css`.

**`components/`** (React primitives — `window.AradQualityIntelligenceDesignSystem_813b73`)
- `core/` — **Button**, **Badge**, **Input**, **Card**
- `feedback/` — **StatusDot** (pulse ring), **ProgressBar**
- `data/` — **KPICard**, **MetricPill**, **SegmentedBar**

**`guidelines/`** — foundation specimen cards (Type, Colors, Spacing, Brand) for the
Design System tab.

**`assets/`** — Arad logo (hexagon mark + wordmark), favicon.

**`ui_kits/app/`** — full click-through recreation of the web app (Dashboard, GR&R Studies,
Review Queue, Alerts, AI Assistant).

---

## CAVEATS
- **Fonts:** Inter substitutes for Geist (brief allowed either); both Inter & JetBrains Mono
  load from Google Fonts CDN rather than self-hosted binaries. Provide `.woff2` files to
  self-host and register `@font-face`.
- **Icons:** Lucide (CDN) substitutes for any proprietary Arad icon set.
- **No source code/Figma** was provided — everything derives from the written brief.
