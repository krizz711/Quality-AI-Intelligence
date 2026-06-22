"use client";

/* Arad UI Kit — TSX port of the prototype component library (app/lib.jsx + charts.jsx).
   Count-up KPI cards, sparklines, glowing cards, donut gauge, SVG SPC chart. */

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

const prefersReduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function fmt(n: number, decimals = 0) {
  return Number(n).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/* count-up that returns {val, done}; restarts whenever animateKey changes */
export function useCountUp(target: number | string, animateKey: unknown, duration = 800) {
  const [val, setVal] = useState<number>(Number(target) || 0);
  const [done, setDone] = useState(true);

  useEffect(() => {
    const num = parseFloat(String(target));
    if (Number.isNaN(num)) {
      setDone(true);
      return;
    }
    if (typeof document === "undefined" || document.visibilityState !== "visible" || prefersReduced()) {
      setVal(num);
      setDone(true);
      return;
    }

    let raf: number;
    let start: number | undefined;
    setDone(false);
    const step = (t: number) => {
      if (!start) {
        start = t;
        setVal(0);
      }
      const p = Math.min((t - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(num * eased);
      if (p < 1) raf = requestAnimationFrame(step);
      else {
        setVal(num);
        setDone(true);
      }
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animateKey, target]);

  return { val, done };
}

/* staggered reveal wrapper */
export function Reveal({
  children,
  delay = 0,
  sm = false,
  className = "",
  style = {},
}: {
  children: ReactNode;
  delay?: number;
  sm?: boolean;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={`${sm ? "arad-reveal-sm" : "arad-reveal"} ${className}`.trim()}
      style={{ "--d": `${delay}ms`, ...style } as CSSProperties}
    >
      {children}
    </div>
  );
}

export function Card({
  children,
  interactive = false,
  accent,
  padding = 24,
  style = {},
}: {
  children: ReactNode;
  interactive?: boolean;
  accent?: "ai" | "info" | "pass" | "conditional" | "fail" | "critical";
  padding?: number;
  style?: CSSProperties;
}) {
  const [hover, setHover] = useState(false);
  const accentColors: Record<string, string> = {
    ai: "var(--accent-ai)",
    info: "var(--accent)",
    pass: "var(--success)",
    conditional: "var(--warning)",
    fail: "var(--critical)",
    critical: "var(--critical)",
  };
  return (
    <div
      onMouseEnter={() => interactive && setHover(true)}
      onMouseLeave={() => interactive && setHover(false)}
      style={{
        background:
          "radial-gradient(120% 90% at 0% 0%, rgba(120,160,255,0.035), transparent 46%), linear-gradient(180deg, rgba(255,255,255,0.022), transparent 36%), var(--bg-surface)",
        border: `1px solid ${hover ? "var(--border-accent)" : "var(--border-default)"}`,
        borderLeft: accent ? `3px solid ${accentColors[accent]}` : undefined,
        borderRadius: "var(--radius-2xl)",
        padding,
        boxShadow: hover ? "var(--shadow-md), var(--edge-highlight-strong)" : "var(--shadow-sm), var(--edge-highlight)",
        transform: hover ? "translateY(-3px)" : "none",
        transition: "box-shadow 320ms var(--ease-out), border-color 220ms var(--ease-out), transform 320ms var(--ease-out)",
        boxSizing: "border-box",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
      <h2 style={{ margin: 0, fontFamily: "var(--font-sans)", fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
        {children}
      </h2>
      <div style={{ flex: 1 }} />
      {right}
    </div>
  );
}

export function StatusDot({
  tone = "success",
  pulse = true,
  size = 8,
  label,
  speed = "1.8s",
}: {
  tone?: "success" | "warning" | "critical" | "info" | "purple" | "muted";
  pulse?: boolean;
  size?: number;
  label?: string;
  speed?: string;
}) {
  const colors: Record<string, string> = {
    success: "var(--success)",
    warning: "var(--warning)",
    critical: "var(--critical)",
    info: "var(--accent)",
    purple: "var(--accent-ai)",
    muted: "var(--text-muted)",
  };
  const c = colors[tone] || colors.success;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span style={{ position: "relative", width: size, height: size, display: "inline-block" }}>
        {pulse && !prefersReduced() && (
          <span
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              background: c,
              animation: `arad-pulse ${speed} var(--ease-out) infinite`,
            }}
          />
        )}
        <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: c, boxShadow: `0 0 6px ${c}` }} />
      </span>
      {label && (
        <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>
          {label}
        </span>
      )}
    </span>
  );
}

export function Sparkline({
  data,
  w = 72,
  h = 28,
  color = "var(--accent)",
  id = "sp",
  showDots = false,
}: {
  data?: number[];
  w?: number;
  h?: number;
  color?: string;
  id?: string;
  showDots?: boolean;
}) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const rng = max - min || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * w, h - ((v - min) / rng) * h]);
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const gid = `grad-${id}`;
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }} aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L${w},${h} L0,${h} Z`} fill={`url(#${gid})`} />
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" />
      {showDots &&
        pts.map((p, i) => (
          <circle key={i} cx={p[0]} cy={p[1]} r="2" fill={color} style={{ animation: `arad-fade-in .3s ${i * 40}ms both` }} />
        ))}
    </svg>
  );
}

export function KPICard({
  label,
  value,
  unit = "",
  subtitle,
  subtitleTone = "muted",
  spark,
  animateKey,
  id = "k",
  delay = 0,
}: {
  label: string;
  value: number | string;
  unit?: string;
  subtitle?: string;
  subtitleTone?: "success" | "warning" | "critical" | "muted" | "info";
  spark?: number[];
  animateKey: unknown;
  id?: string;
  delay?: number;
}) {
  const { val, done } = useCountUp(value, animateKey, 800);
  const [hover, setHover] = useState(false);
  const numeric = !Number.isNaN(parseFloat(String(value)));
  const display = numeric ? fmt(val, String(value).includes(".") ? 1 : 0) : String(value);
  const toneColors: Record<string, string> = {
    success: "var(--success)",
    warning: "var(--warning)",
    critical: "var(--critical)",
    muted: "var(--text-secondary)",
    info: "var(--accent)",
  };
  return (
    <div
      className="arad-kpi-in"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={
        {
          "--d": `${delay}ms`,
          position: "relative",
          background:
            "radial-gradient(120% 90% at 0% 0%, rgba(120,160,255,0.04), transparent 46%), linear-gradient(180deg, rgba(255,255,255,0.022), transparent 38%), var(--bg-surface)",
          border: `1px solid ${hover ? "var(--border-accent)" : "var(--border-default)"}`,
          borderRadius: "var(--radius-2xl)",
          padding: 24,
          boxShadow: hover ? "var(--shadow-md), var(--edge-highlight-strong)" : "var(--shadow-sm), var(--edge-highlight)",
          transform: hover ? "translateY(-3px)" : "none",
          transition: "box-shadow 320ms var(--ease-out), border-color 220ms var(--ease-out), transform 320ms var(--ease-out)",
          minHeight: 122,
          boxSizing: "border-box",
          overflow: "hidden",
        } as CSSProperties
      }
    >
      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: ".08em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
          marginBottom: 12,
        }}
      >
        {label}
      </div>
      <div
        key={String(done)}
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 30,
          fontWeight: 600,
          color: "var(--text-primary)",
          lineHeight: 1,
          letterSpacing: "-.01em",
          animation: done && numeric && !prefersReduced() ? "arad-flash-text .55s ease-out" : "none",
        }}
      >
        {display}
        {unit ? <span style={{ fontSize: 16, color: "var(--text-secondary)", marginLeft: 2 }}>{unit}</span> : null}
      </div>
      {subtitle && (
        <div
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 13,
            fontWeight: 500,
            color: toneColors[subtitleTone],
            marginTop: 10,
            paddingRight: spark ? 80 : 0,
          }}
        >
          {subtitle}
        </div>
      )}
      {spark && (
        <div style={{ position: "absolute", right: 16, bottom: 16 }}>
          <Sparkline data={spark} id={id} showDots={hover} />
        </div>
      )}
    </div>
  );
}

export function MetricPill({
  value,
  label,
  tone = "default",
  delay,
}: {
  value: string | number;
  label: string;
  tone?: "default" | "success" | "warning" | "critical" | "info";
  delay?: number;
}) {
  const toneColors: Record<string, string> = {
    default: "var(--text-primary)",
    success: "var(--success)",
    warning: "var(--warning)",
    critical: "var(--critical)",
    info: "var(--accent)",
  };
  return (
    <div
      className={delay != null ? "arad-reveal-sm" : ""}
      style={
        {
          "--d": `${delay || 0}ms`,
          flex: 1,
          minWidth: 96,
          background: "var(--bg-primary)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          padding: "12px 14px",
          boxSizing: "border-box",
        } as CSSProperties
      }
    >
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 600, color: toneColors[tone], lineHeight: 1.1 }}>
        {value}
      </div>
      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: 12,
          letterSpacing: ".08em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
          marginTop: 6,
        }}
      >
        {label}
      </div>
    </div>
  );
}

/* SegmentedBar with grow-in animation; each segment grows after the previous */
export function SegmentedBar({
  segments,
  height = 28,
  showLabels = true,
  animate = false,
}: {
  segments: { label: string; value: number; color?: string }[];
  height?: number;
  showLabels?: boolean;
  animate?: boolean;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const palette = ["var(--accent)", "var(--accent-ai)", "var(--success)", "var(--warning)"];
  const [grown, setGrown] = useState(!animate);
  useEffect(() => {
    if (animate) {
      const t = setTimeout(() => setGrown(true), 60);
      return () => clearTimeout(t);
    }
  }, [animate]);
  return (
    <div>
      <div
        style={{
          display: "flex",
          height,
          borderRadius: "var(--radius-sm)",
          overflow: "hidden",
          border: "1px solid var(--border-default)",
        }}
      >
        {segments.map((s, i) => {
          const pct = (s.value / total) * 100;
          return (
            <div
              key={i}
              style={{
                width: grown ? `${pct}%` : "0%",
                background: s.color || palette[i % palette.length],
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                fontWeight: 600,
                color: "rgba(255,255,255,.92)",
                overflow: "hidden",
                whiteSpace: "nowrap",
                transition: `width ${i === 0 ? 420 : 320}ms var(--ease-out)`,
                transitionDelay: `${i * 120}ms`,
              }}
            >
              {pct > 10 ? `${Math.round(s.value)}%` : ""}
            </div>
          );
        })}
      </div>
      {showLabels && (
        <div style={{ display: "flex", gap: 16, marginTop: 10, flexWrap: "wrap" }}>
          {segments.map((s, i) => (
            <span
              key={i}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--text-secondary)" }}
            >
              <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color || palette[i % palette.length] }} />
              {s.label} <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{Math.round(s.value)}%</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Step indicator: active dot expands, completed draws a check ── */
export function StepDots({ step, steps = ["Setup", "Data", "Run"] }: { step: number; steps?: string[] }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {steps.map((s, i) => {
        const n = i + 1;
        const done = n < step;
        const active = n === step;
        return (
          <span key={s} style={{ display: "contents" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span
                style={{
                  position: "relative",
                  height: 20,
                  minWidth: 20,
                  width: active ? 22 : 20,
                  borderRadius: 999,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                  background: done || active ? "var(--accent)" : "var(--bg-primary)",
                  color: done || active ? "#fff" : "var(--text-muted)",
                  border: done || active ? "none" : "1px solid var(--border-default)",
                  transition: "all .25s var(--ease-out)",
                }}
              >
                {done ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                ) : (
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600 }}>{n}</span>
                )}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: 12,
                  fontWeight: 500,
                  color: done || active ? "var(--text-primary)" : "var(--text-muted)",
                  transition: "color .2s",
                }}
              >
                {s}
              </span>
            </span>
            {i < steps.length - 1 && (
              <span style={{ width: 18, height: 2, borderRadius: 2, background: "var(--border-default)", overflow: "hidden", display: "inline-block" }}>
                <span style={{ display: "block", height: "100%", width: done ? "100%" : "0%", background: "var(--accent)", transition: "width .3s var(--ease-out)" }} />
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}

/* ── streams children in one-by-one ── */
export function Stream({ items, step = 110, restartKey }: { items: ReactNode[]; step?: number; restartKey: unknown }) {
  const [n, setN] = useState(prefersReduced() ? items.length : 0);
  useEffect(() => {
    if (prefersReduced()) {
      setN(items.length);
      return;
    }
    setN(0);
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setN(i);
      if (i >= items.length) clearInterval(iv);
    }, step);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restartKey]);
  return (
    <>
      {items.map((node, i) => (
        <div
          key={i}
          style={{
            opacity: i < n ? 1 : 0,
            transform: i < n ? "none" : "translateY(4px)",
            transition: "opacity .25s var(--ease-out), transform .25s var(--ease-out)",
          }}
        >
          {node}
        </div>
      ))}
    </>
  );
}

export function LoadingDots({ color = "#fff" }: { color?: string }) {
  return (
    <span style={{ display: "inline-flex", gap: 3, alignItems: "center" }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{ width: 4, height: 4, borderRadius: 999, background: color, animation: `arad-typing 1.1s ${i * 0.15}s infinite` }}
        />
      ))}
    </span>
  );
}

/* ── Donut gauge: arc draws clockwise, number counts up ── */
export function DonutGauge({
  value,
  size = 150,
  animateKey = 0,
  caption = "Accuracy",
}: {
  value: number;
  size?: number;
  animateKey?: unknown;
  caption?: string;
}) {
  const r = size / 2 - 12;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  const { val } = useCountUp(value, animateKey, 850);
  const passLen = (val / 100) * circ;
  const failLen = ((100 - val) / 100) * circ;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }} aria-hidden="true">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--bg-primary)" strokeWidth="10" />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#ef4444"
          strokeWidth="10"
          strokeDasharray={`${failLen} ${circ}`}
          strokeDashoffset={-passLen}
          opacity="0.85"
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#10b981"
          strokeWidth="10"
          strokeDasharray={`${passLen} ${circ}`}
          strokeLinecap="round"
          style={{ filter: "drop-shadow(0 0 5px rgba(16,185,129,.5))" }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 600, color: "var(--text-primary)" }}>
          {val.toFixed(1)}%
        </div>
        <div
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 11,
            letterSpacing: ".06em",
            textTransform: "uppercase",
            color: "var(--text-muted)",
            marginTop: 2,
          }}
        >
          {caption}
        </div>
      </div>
    </div>
  );
}

/* ── SPC control chart: draw-in line, pulsing violations, SVG-native tooltip ── */
export interface SPCChartPoint {
  v: number;
  violation?: boolean;
  violationLabel?: string;
}

export function SPCChart({
  data,
  ucl,
  cl,
  lcl,
  height = 280,
  drawKey = 0,
}: {
  data: SPCChartPoint[];
  ucl: number;
  cl: number;
  lcl: number;
  height?: number;
  drawKey?: number;
}) {
  const W = 820;
  const H = height;
  const padL = 52;
  const padR = 16;
  const padT = 18;
  const padB = 28;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const [hover, setHover] = useState<number | null>(null);
  const [seen, setSeen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || seen) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true);
          io.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    io.observe(ref.current);
    return () => io.disconnect();
  }, [seen]);

  if (data.length < 2) return null;

  const reduce = prefersReduced();
  const vals = data.map((d) => d.v);
  const lo = Math.min(lcl, ...vals) - (ucl - lcl) * 0.18;
  const hi = Math.max(ucl, ...vals) + (ucl - lcl) * 0.18;
  const rng = hi - lo || 1;
  const x = (i: number) => padL + (i / (data.length - 1)) * plotW;
  const y = (v: number) => padT + (1 - (v - lo) / rng) * plotH;
  const linePath = data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d.v).toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${x(data.length - 1).toFixed(1)},${(padT + plotH).toFixed(1)} L${padL},${(padT + plotH).toFixed(1)} Z`;
  const DRAW = 600;
  const active = seen && !reduce;
  const lastIdx = data.length - 1;

  const limitLine = (val: number, color: string, labelTxt: string, delay: number) => (
    <g style={{ animation: active ? `arad-fade-in .3s ${delay}ms both` : "none" }}>
      <line x1={padL} y1={y(val)} x2={W - padR} y2={y(val)} stroke={color} strokeWidth="1" strokeDasharray="5 4" opacity="0.7" />
      <text x={W - padR} y={y(val) - 4} textAnchor="end" fontFamily="var(--font-mono)" fontSize="10" fill={color} opacity="0.9">
        {labelTxt} {val.toFixed(3)}
      </text>
    </g>
  );

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block", overflow: "visible" }} role="img" aria-label="SPC control chart">
        <defs>
          <linearGradient id="spcFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.16" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[lo, lo + rng * 0.25, lo + rng * 0.5, lo + rng * 0.75, hi].map((v, i) => (
          <text key={i} x={padL - 8} y={y(v) + 3} textAnchor="end" fontFamily="var(--font-mono)" fontSize="10" fill="var(--text-muted)">
            {v.toFixed(2)}
          </text>
        ))}
        {limitLine(ucl, "#ef4444", "UCL", DRAW + 200)}
        {limitLine(cl, "#3b82f6", "CL", DRAW + 200)}
        {limitLine(lcl, "#ef4444", "LCL", DRAW + 200)}
        <path
          d={areaPath}
          fill="url(#spcFill)"
          style={{ opacity: active ? 0 : 1, animation: active ? `arad-fade-in .3s ${DRAW}ms forwards` : "none" }}
        />
        <path
          key={drawKey}
          d={linePath}
          fill="none"
          stroke="#f1f5f9"
          strokeWidth="1.5"
          pathLength={1}
          style={
            active
              ? { strokeDasharray: 1, strokeDashoffset: 1, animation: `arad-spc-draw ${drawKey ? 420 : DRAW}ms var(--ease-out) forwards` }
              : {}
          }
        />
        {data.map((d, i) => {
          const ptDelay = active ? (drawKey ? 0 : (i / lastIdx) * DRAW) : 0;
          const isNewest = drawKey > 0 && i === lastIdx;
          const enlarge = hover === i;
          const commonStyle: CSSProperties = {
            transformBox: "fill-box",
            transformOrigin: "center",
            animation: active && !isNewest ? `arad-pt-pop .2s ${ptDelay}ms var(--ease-out) both` : "none",
            cursor: "pointer",
            transition: "transform .15s var(--ease-out)",
            transform: enlarge ? "scale(1.5)" : "scale(1)",
          };
          if (d.violation) {
            return (
              <g key={i}>
                <circle cx={x(i)} cy={y(d.v)} r="6" fill="none" stroke="#ef4444" strokeWidth="1.5">
                  <animate attributeName="r" values="5;13;5" dur="1.6s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.8;0;0.8" dur="1.6s" repeatCount="indefinite" />
                </circle>
                <circle
                  cx={x(i)}
                  cy={y(d.v)}
                  r="3.6"
                  fill="#ef4444"
                  stroke="#0a0b0f"
                  strokeWidth="1"
                  style={commonStyle}
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                />
              </g>
            );
          }
          return (
            <circle
              key={i}
              cx={x(i)}
              cy={y(d.v)}
              r="3"
              fill={isNewest ? "#3b82f6" : "#94a3b8"}
              style={{ ...commonStyle, animation: isNewest ? "arad-slide-in-x .4s var(--ease-out) both" : commonStyle.animation }}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
        {hover != null &&
          (() => {
            const d = data[hover];
            const px = x(hover);
            const py = y(d.v);
            const left = px > W - 150;
            const tw = 132;
            const tx = left ? px - tw - 10 : px + 10;
            const ty = Math.max(py - 46, padT);
            return (
              <g style={{ pointerEvents: "none" }}>
                <rect x={tx} y={ty} width={tw} height={42} rx="6" fill="#181c24" stroke="#3b82f6" strokeWidth="1" opacity="0.98" />
                <text x={tx + 11} y={ty + 17} fontFamily="var(--font-sans)" fontSize="10" fill="#94a3b8">
                  Measurement {hover + 1}
                </text>
                <text
                  x={tx + 11}
                  y={ty + 33}
                  fontFamily="var(--font-mono)"
                  fontSize="13"
                  fontWeight="600"
                  fill={d.violation ? "#f87171" : "#f1f5f9"}
                >
                  {d.v.toFixed(3)}
                  {d.violation ? "  ✗" : ""}
                </text>
              </g>
            );
          })()}
      </svg>
    </div>
  );
}
