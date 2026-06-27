#!/usr/bin/env python3
"""Generate docs/assets/architecture.svg — a professional system-architecture
diagram for Quality AI Intelligence with embedded brand logos.

Run from anywhere:  python docs/assets/build_architecture.py

Brand icons are read from docs/assets/icons/ (Simple Icons) and each icon's
vector path is *inlined*, so the output is a single self-contained SVG that
renders on GitHub (no external image references).
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
ICONS = ROOT / "icons"
OUT = ROOT / "architecture.svg"

W, H = 1080, 840
FONT = "Segoe UI, Roboto, Helvetica, Arial, sans-serif"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ipath(slug: str) -> str:
    svg = (ICONS / f"{slug}.svg").read_text(encoding="utf-8")
    m = re.search(r'<path[^>]*\bd="([^"]+)"', svg)
    if not m:
        raise SystemExit(f"no <path> found in {slug}.svg")
    return m.group(1)


def brand(slug: str, cx: float, cy: float, size: float, color: str) -> str:
    d = ipath(slug)
    x, y = cx - size / 2, cy - size / 2
    return (
        f'<svg x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" '
        f'viewBox="0 0 24 24"><path fill="{color}" d="{d}"/></svg>'
    )


def text(x, y, s, size=12.5, color="#1E293B", weight="600", anchor="middle", spacing=0.0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}"{sp}>{esc(s)}</text>'
    )


def label(cx, y0, lines, size=12.5, color="#1E293B", weight="600"):
    return "".join(text(cx, y0 + i * 14.5, ln, size, color, weight) for i, ln in enumerate(lines))


def card(cx, top, w, h, lines, accent, icon_svg, label_size=12.5):
    x = cx - w / 2
    shadow = f'<rect x="{x + 1:.1f}" y="{top + 3:.1f}" width="{w}" height="{h}" rx="13" fill="#0F172A" opacity="0.06"/>'
    rect = (
        f'<rect x="{x:.1f}" y="{top}" width="{w}" height="{h}" rx="13" '
        f'fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1.2"/>'
    )
    bar = f'<rect x="{x:.1f}" y="{top}" width="{w}" height="4" rx="2" fill="{accent}"/>'
    lines_y = top + h - (len(lines) * 14.5) - 2
    return shadow + rect + bar + icon_svg + label(cx, lines_y, lines, size=label_size)


def band(top, h, label_text, accent, x=32, w=W - 64):
    cont = (
        f'<rect x="{x}" y="{top}" width="{w}" height="{h}" rx="18" '
        f'fill="#FFFFFF" opacity="0.55" stroke="#E2E8F0" stroke-width="1"/>'
    )
    chip_w = 22 + len(label_text) * 7.1
    chip = (
        f'<rect x="{x + 16:.1f}" y="{top - 12:.1f}" width="{chip_w:.0f}" height="24" rx="12" fill="{accent}"/>'
        + text(x + 16 + chip_w / 2, top + 4, label_text, size=11.5, color="#FFFFFF", weight="700", spacing="0.6")
    )
    return cont + chip


def centers(x_left, x_right, n, card_w):
    inner = x_right - x_left
    gap = (inner - n * card_w) / (n + 1)
    return [x_left + gap * (i + 1) + card_w * (i + 0.5) for i in range(n)]


def varrow(cx, y1, y2, lbl=None, c="#94A3B8"):
    s = (
        f'<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{y2 - 9}" stroke="{c}" stroke-width="2.2"/>'
        f'<path d="M{cx - 6},{y2 - 9} L{cx + 6},{y2 - 9} L{cx},{y2} Z" fill="{c}"/>'
    )
    if lbl:
        my = (y1 + y2) / 2
        wl = 16 + len(lbl) * 6.3
        s += (
            f'<rect x="{cx - wl / 2:.1f}" y="{my - 10:.1f}" width="{wl:.0f}" height="20" rx="10" '
            f'fill="#FFFFFF" stroke="#E2E8F0"/>'
            + text(cx, my + 4, lbl, size=11, color="#475569", weight="600")
        )
    return s


def harrow2(x1, x2, cy, lbl=None, c="#94A3B8"):
    s = (
        f'<line x1="{x1 + 9}" y1="{cy}" x2="{x2 - 9}" y2="{cy}" stroke="{c}" stroke-width="2.2"/>'
        f'<path d="M{x1 + 9},{cy - 6} L{x1 + 9},{cy + 6} L{x1},{cy} Z" fill="{c}"/>'
        f'<path d="M{x2 - 9},{cy - 6} L{x2 - 9},{cy + 6} L{x2},{cy} Z" fill="{c}"/>'
    )
    if lbl:
        mx = (x1 + x2) / 2
        s += text(mx, cy - 8, lbl, size=10.5, color="#64748B", weight="600")
    return s


# ── Hand-drawn glyphs for non-brand nodes (concepts, not products) ──────────────
def g_doc(cx, cy, c):
    x, y = cx - 9, cy - 12
    return (
        f'<g stroke="{c}" stroke-width="1.8" fill="none" stroke-linejoin="round" stroke-linecap="round">'
        f'<path d="M{x},{y} h10 l6,6 v16 h-16 z"/><path d="M{x + 10},{y} v6 h6"/>'
        f'<path d="M{x + 3},{y + 12} h9 M{x + 3},{y + 16} h9 M{x + 3},{y + 20} h6"/></g>'
    )


def g_server(cx, cy, c):
    x = cx - 11
    return (
        f'<g stroke="{c}" stroke-width="1.7" fill="none"><rect x="{x}" y="{cy - 11}" width="22" height="9" rx="2.5"/>'
        f'<rect x="{x}" y="{cy + 2}" width="22" height="9" rx="2.5"/></g>'
        f'<circle cx="{x + 5}" cy="{cy - 6.5}" r="1.5" fill="{c}"/><circle cx="{x + 5}" cy="{cy + 6.5}" r="1.5" fill="{c}"/>'
    )


def g_bolt(cx, cy, c):
    return f'<path d="M{cx + 3},{cy - 12} L{cx - 6},{cy + 3} L{cx - 1},{cy + 3} L{cx - 3},{cy + 12} L{cx + 7},{cy - 3} L{cx + 1},{cy - 3} Z" fill="{c}"/>'


def g_env(cx, cy, c):
    x, y = cx - 12, cy - 9
    return (
        f'<g stroke="{c}" stroke-width="1.7" fill="none" stroke-linejoin="round">'
        f'<rect x="{x}" y="{y}" width="24" height="18" rx="2.5"/><path d="M{x + 1},{y + 1.5} l11,8 l11,-8"/></g>'
    )


def g_gauge(cx, cy, c):
    return (
        f'<g stroke="{c}" stroke-width="1.9" fill="none" stroke-linecap="round">'
        f'<path d="M{cx - 11},{cy + 6} A11,11 0 0 1 {cx + 11},{cy + 6}"/>'
        f'<line x1="{cx}" y1="{cy + 6}" x2="{cx + 6}" y2="{cy - 4}"/></g>'
        f'<circle cx="{cx}" cy="{cy + 6}" r="2" fill="{c}"/>'
    )


def g_chart(cx, cy, c):
    x, b = cx - 11, cy + 9
    return (
        f'<g stroke="{c}" stroke-width="1.9" fill="none" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M{x},{cy - 11} V{b} H{x + 22}"/><path d="M{x + 3},{cy + 2} l5,-6 l5,4 l6,-9"/></g>'
    )


def g_radar(cx, cy, c):
    return (
        f'<g stroke="{c}" stroke-width="1.7" fill="none"><circle cx="{cx}" cy="{cy}" r="11"/>'
        f'<circle cx="{cx}" cy="{cy}" r="6"/></g><circle cx="{cx}" cy="{cy}" r="2.3" fill="{c}"/>'
    )


# ── Palette ─────────────────────────────────────────────────────────────────
SKY, INDIGO, EMERALD, AMBER, VIOLET, PINK = "#0EA5E9", "#6366F1", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"
SLATE = "#64748B"

p = [f'<rect width="{W}" height="{H}" fill="#F1F5F9"/>',
     f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="6" fill="none" stroke="#E2E8F0"/>']

# Title
p.append(text(W / 2, 42, "Quality AI Intelligence", size=27, color="#0F172A", weight="800"))
p.append(text(W / 2, 66, "System Architecture — automated GR&R, SPC, and 24/7 alerting", size=13, color="#64748B", weight="500"))

CW = 212  # standard card width

# Band 1 — Data ingress
b1 = 100
p.append(band(b1, 104, "DATA INGRESS", SKY))
xs = centers(48, W - 48, 4, CW)
p.append(card(xs[0], b1 + 8, CW, 88, ["Apache Kafka", "stream"], SKY, brand("apachekafka", xs[0], b1 + 36, 30, "#231F20")))
p.append(card(xs[1], b1 + 8, CW, 88, ["CSV / Excel", "upload"], SKY, g_doc(xs[1], b1 + 36, "#0284C7")))
p.append(card(xs[2], b1 + 8, CW, 88, ["MES / QMS", "auto-pull (timed)"], SKY, g_server(xs[2], b1 + 36, "#0284C7")))
p.append(card(xs[3], b1 + 8, CW, 88, ["REST", "push"], SKY, g_bolt(xs[3], b1 + 36, "#0284C7")))

# Band 2 — API service (narrower; dashboard sits to the right)
b2 = 232
b2w = 730
p.append(band(b2, 150, "ARAD API SERVICE", INDIGO, x=32, w=b2w))
p.append(brand("fastapi", 70, b2 + 26, 22, "#009688"))
p.append(text(88, b2 + 30, "FastAPI runtime · REST API · auth · encrypted settings", size=11.5, color="#475569", weight="600", anchor="start"))
sx = centers(48, 32 + b2w - 16, 4, 160)
sub_top = b2 + 50
p.append(card(sx[0], sub_top, 160, 86, ["GR&R engine", "AIAG Xbar-R"], INDIGO, g_gauge(sx[0], sub_top + 30, INDIGO), 12))
p.append(card(sx[1], sub_top, 160, 86, ["SPC engine", "I-MR + Nelson"], INDIGO, g_chart(sx[1], sub_top + 30, INDIGO), 12))
p.append(card(sx[2], sub_top, 160, 86, ["Autonomous", "monitor · 30s"], INDIGO, g_radar(sx[2], sub_top + 30, INDIGO), 12))
# AI router subcard — shows the three real provider logos
ai = sx[3]
p.append(card(ai, sub_top, 160, 86, [], INDIGO, "", 12))
p.append(brand("googlegemini", ai - 27, sub_top + 30, 22, "#8E75B2"))
p.append(brand("anthropic", ai, sub_top + 30, 22, "#D97757"))
p.append(brand("openai", ai + 27, sub_top + 30, 22, "#111827"))
p.append(text(ai, sub_top + 68, "AI summary router", size=11.5, color="#1E293B", weight="600"))

# Dashboard (frontend) — to the right of the API band
dx = 32 + b2w + 38
dw = (W - 48) - dx
dcx = dx + dw / 2
p.append(text(dx + 4, b2 - 2, "FRONTEND", size=11, color=PINK, weight="700", anchor="start", spacing="0.6"))
p.append(card(dcx, b2, dw, 150, ["Dashboard", "Next.js"], PINK, brand("nextdotjs", dcx, b2 + 58, 34, "#000000"), 13))
p.append(harrow2(32 + b2w, dx, b2 + 75, "REST"))

# Band 3 — Storage
b3 = 416
p.append(band(b3, 104, "STORAGE", EMERALD))
xs = centers(48, W - 48, 2, 260)
p.append(card(xs[0], b3 + 8, 260, 88, ["TimescaleDB", "hypertable · settings · audit"], EMERALD, brand("timescale", xs[0], b3 + 36, 30, "#C77A0A"), 11.5))
p.append(card(xs[1], b3 + 8, 260, 88, ["Redis", "cache · rate-limit"], EMERALD, brand("redis", xs[1], b3 + 36, 30, "#DC382D")))

# Band 4 — Alert destinations
b4 = 548
p.append(band(b4, 104, "ALERT DESTINATIONS", AMBER))
xs = centers(48, W - 48, 4, CW)
p.append(card(xs[0], b4 + 8, CW, 88, ["Slack", "channel alerts"], AMBER, brand("slack", xs[0], b4 + 36, 30, "#4A154B")))
p.append(card(xs[1], b4 + 8, CW, 88, ["Email", "SMTP"], AMBER, g_env(xs[1], b4 + 36, "#B45309")))
p.append(card(xs[2], b4 + 8, CW, 88, ["SMS", "Twilio"], AMBER, brand("twilio", xs[2], b4 + 36, 30, "#F22F46")))
p.append(card(xs[3], b4 + 8, CW, 88, ["JIRA", "auto ticket"], AMBER, brand("jira", xs[3], b4 + 36, 30, "#0052CC")))

# Band 5 — Observability
b5 = 680
p.append(band(b5, 104, "OBSERVABILITY", VIOLET))
xs = centers(48, W - 48, 3, CW)
p.append(card(xs[0], b5 + 8, CW, 88, ["Prometheus", "metrics"], VIOLET, brand("prometheus", xs[0], b5 + 36, 30, "#E6522C")))
p.append(card(xs[1], b5 + 8, CW, 88, ["Grafana", "dashboards"], VIOLET, brand("grafana", xs[1], b5 + 36, 30, "#F46800")))
p.append(card(xs[2], b5 + 8, CW, 88, ["MLflow", "model tracking"], VIOLET, brand("mlflow", xs[2], b5 + 36, 30, "#0194E2")))

# Flow arrows down the spine
p.append(varrow(W / 2, b1 + 104, b2, "measurements"))
p.append(varrow(W / 2, b2 + 150, b3, "persist"))
p.append(varrow(W / 2, b3 + 104, b4, "detect → alert"))
p.append(varrow(W / 2, b4 + 104, b5, "telemetry", c="#CBD5E1"))

# Footer — Docker platform strip
fy = b5 + 112
p.append(f'<rect x="32" y="{fy}" width="{W - 64}" height="34" rx="10" fill="#0B1220"/>')
p.append(brand("docker", 60, fy + 17, 22, "#2496ED"))
p.append(text(80, fy + 21, "All services orchestrated by Docker Compose — one command to run the whole stack", size=12, color="#E2E8F0", weight="600", anchor="start"))

svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">' + "".join(p) + "</svg>"
OUT.write_text(svg, encoding="utf-8")
print(f"wrote {OUT} ({len(svg)} bytes)")
