/* @ds-bundle: {"format":3,"namespace":"AradQualityIntelligenceDesignSystem_813b73","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"Input","sourcePath":"components/core/Input.jsx"},{"name":"KPICard","sourcePath":"components/data/KPICard.jsx"},{"name":"MetricPill","sourcePath":"components/data/MetricPill.jsx"},{"name":"SegmentedBar","sourcePath":"components/data/SegmentedBar.jsx"},{"name":"ProgressBar","sourcePath":"components/feedback/ProgressBar.jsx"},{"name":"StatusDot","sourcePath":"components/feedback/StatusDot.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"64edb8299f21","components/core/Button.jsx":"133c1ba531d2","components/core/Card.jsx":"5154138c65b7","components/core/Input.jsx":"e51ac5f443a1","components/data/KPICard.jsx":"cc795273a973","components/data/MetricPill.jsx":"36cda6ae6723","components/data/SegmentedBar.jsx":"a4dc0d7b035b","components/feedback/ProgressBar.jsx":"876b46d428a2","components/feedback/StatusDot.jsx":"505c0fbd5c0c","ui_kits/app/Alerts.jsx":"c4cff7e345c9","ui_kits/app/Assistant.jsx":"7d6dbec20f53","ui_kits/app/Dashboard.jsx":"2c1eb2006c81","ui_kits/app/GRRStudies.jsx":"e9a9e3878060","ui_kits/app/ReviewQueue.jsx":"c2885c3f97a7","ui_kits/app/charts.jsx":"dbd6af206acb","ui_kits/app/lib.jsx":"3fb9d04355fd","ui_kits/app/shell.jsx":"2fb656442b22"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.AradQualityIntelligenceDesignSystem_813b73 = window.AradQualityIntelligenceDesignSystem_813b73 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Status pill. tone maps to the Arad semantic palette. variant:
 * "solid" (filled bg + text) or "outline" (transparent bg + colored border/text).
 */
function Badge({
  children,
  tone = 'info',
  variant = 'solid',
  style = {},
  ...rest
}) {
  const tones = {
    pass: {
      bg: 'var(--color-pass-bg)',
      fg: 'var(--color-pass-text)'
    },
    conditional: {
      bg: 'var(--color-cond-bg)',
      fg: 'var(--color-cond-text)'
    },
    fail: {
      bg: 'var(--color-fail-bg)',
      fg: 'var(--color-fail-text)'
    },
    critical: {
      bg: 'var(--color-fail-bg)',
      fg: 'var(--color-fail-text)'
    },
    info: {
      bg: 'var(--color-info-bg)',
      fg: 'var(--color-info-text)'
    },
    purple: {
      bg: 'var(--color-purple-bg)',
      fg: 'var(--color-purple-text)'
    },
    neutral: {
      bg: 'var(--color-surface-elevated)',
      fg: 'var(--color-text-secondary)'
    }
  };
  const t = tones[tone] || tones.info;
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontFamily: 'var(--font-sans)',
    fontSize: 'var(--text-caption)',
    fontWeight: 'var(--weight-semibold)',
    letterSpacing: 'var(--tracking-caps)',
    textTransform: 'uppercase',
    lineHeight: 1,
    padding: '4px 8px',
    borderRadius: 'var(--radius-sm)'
  };
  const skin = variant === 'outline' ? {
    background: 'transparent',
    color: t.fg,
    border: `1px solid ${t.fg}`,
    opacity: 0.95
  } : {
    background: t.bg,
    color: t.fg,
    border: '1px solid transparent'
  };
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      ...base,
      ...skin,
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Arad primary action button. Variants: primary (blue gradient),
 * secondary (dark + blue border), destructive, ghost. Sizes: sm | md.
 */
function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon = null,
  disabled = false,
  type = 'button',
  onClick,
  style = {},
  ...rest
}) {
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--space-2)',
    fontFamily: 'var(--font-sans)',
    fontWeight: 'var(--weight-medium)',
    fontSize: size === 'sm' ? '12px' : 'var(--text-body)',
    height: size === 'sm' ? '28px' : 'var(--control-height)',
    padding: size === 'sm' ? '0 10px' : '0 14px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid transparent',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'background var(--transition), border-color var(--transition), box-shadow var(--transition), transform var(--transition)',
    whiteSpace: 'nowrap',
    userSelect: 'none'
  };
  const variants = {
    primary: {
      background: 'linear-gradient(180deg, var(--color-primary) 0%, var(--color-primary-hover) 100%)',
      color: '#fff',
      boxShadow: '0 1px 2px rgba(0,0,10,0.4)'
    },
    secondary: {
      background: 'var(--color-surface-elevated)',
      border: '1px solid rgba(59,130,246,0.4)',
      color: 'var(--color-primary)'
    },
    destructive: {
      background: '#7F1D1D',
      color: '#FCA5A5'
    },
    ghost: {
      background: 'transparent',
      color: 'var(--color-text-secondary)'
    }
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    disabled: disabled,
    onClick: onClick,
    style: {
      ...base,
      ...variants[variant],
      ...style
    },
    onMouseEnter: e => {
      if (disabled) return;
      if (variant === 'ghost') e.currentTarget.style.background = 'var(--color-surface-elevated)';
      if (variant === 'secondary') e.currentTarget.style.boxShadow = 'var(--glow-primary)';
      if (variant === 'primary') e.currentTarget.style.filter = 'brightness(1.08)';
    },
    onMouseLeave: e => {
      if (variant === 'ghost') e.currentTarget.style.background = 'transparent';
      if (variant === 'secondary') e.currentTarget.style.boxShadow = 'none';
      if (variant === 'primary') e.currentTarget.style.filter = 'none';
    }
  }, rest), icon, children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useState
} = React;
/**
 * Surface container. `interactive` adds a blue glow on hover.
 * `accent` draws a 3px left border ("ai" indigo, "info" blue, semantic tones).
 */
function Card({
  children,
  interactive = false,
  accent = null,
  elevated = false,
  padding = 'var(--space-5)',
  style = {},
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const accentColors = {
    ai: 'var(--color-secondary)',
    info: 'var(--color-primary)',
    pass: 'var(--color-success)',
    conditional: 'var(--color-warning)',
    fail: 'var(--color-critical)',
    critical: 'var(--color-critical)'
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    onMouseEnter: () => interactive && setHover(true),
    onMouseLeave: () => interactive && setHover(false),
    style: {
      background: elevated ? 'var(--color-surface-elevated)' : 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderLeft: accent ? `3px solid ${accentColors[accent] || accent}` : '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      padding,
      boxShadow: hover ? 'var(--glow-primary)' : 'var(--shadow-sm)',
      transition: 'box-shadow var(--transition), border-color var(--transition)',
      boxSizing: 'border-box',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useState
} = React;
/**
 * Form text input with floating-caps label, blue focus ring and inline error.
 * Pass `mono` for measurement / numeric fields.
 */
function Input({
  label,
  error,
  hint,
  mono = false,
  value,
  onChange,
  placeholder,
  type = 'text',
  disabled = false,
  style = {},
  ...rest
}) {
  const [focused, setFocused] = useState(false);
  const borderColor = error ? 'var(--color-critical)' : focused ? 'var(--ring-focus-border)' : 'var(--color-border)';
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      fontWeight: 'var(--weight-semibold)',
      letterSpacing: 'var(--tracking-caps)',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)'
    }
  }, label), /*#__PURE__*/React.createElement("input", _extends({
    type: type,
    value: value,
    onChange: onChange,
    placeholder: placeholder,
    disabled: disabled,
    onFocus: () => setFocused(true),
    onBlur: () => setFocused(false),
    style: {
      height: 'var(--input-height)',
      padding: '0 12px',
      background: 'var(--color-surface-inset)',
      border: `1px solid ${borderColor}`,
      borderRadius: 'var(--radius-md)',
      color: 'var(--color-text)',
      fontFamily: mono ? 'var(--font-mono)' : 'var(--font-sans)',
      fontSize: 'var(--text-body)',
      outline: 'none',
      boxShadow: focused && !error ? 'var(--ring-focus)' : 'none',
      transition: 'border-color var(--transition), box-shadow var(--transition)',
      opacity: disabled ? 0.5 : 1,
      width: '100%',
      boxSizing: 'border-box'
    }
  }, rest)), error ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      color: 'var(--color-fail-text)'
    }
  }, error) : hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      color: 'var(--color-text-muted)'
    }
  }, hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Input.jsx", error: String((e && e.message) || e) }); }

// components/data/KPICard.jsx
try { (() => {
/**
 * Dashboard KPI tile: big monospace number, colored delta/subtitle line,
 * and an optional inline sparkline (pass an array of numbers to `spark`).
 */
function KPICard({
  label,
  value,
  unit = '',
  subtitle = null,
  subtitleTone = 'muted',
  spark = null,
  style = {}
}) {
  const toneColors = {
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    muted: 'var(--color-text-secondary)',
    info: 'var(--color-primary)'
  };
  const sc = toneColors[subtitleTone] || toneColors.muted;

  // build sparkline path
  let sparkEl = null;
  if (spark && spark.length > 1) {
    const w = 72,
      h = 28,
      min = Math.min(...spark),
      max = Math.max(...spark);
    const rng = max - min || 1;
    const pts = spark.map((v, i) => [i / (spark.length - 1) * w, h - (v - min) / rng * h]);
    const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
    const area = `${d} L${w},${h} L0,${h} Z`;
    sparkEl = /*#__PURE__*/React.createElement("svg", {
      width: w,
      height: h,
      style: {
        position: 'absolute',
        right: 16,
        bottom: 16,
        overflow: 'visible'
      }
    }, /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("linearGradient", {
      id: "arad-spark",
      x1: "0",
      y1: "0",
      x2: "0",
      y2: "1"
    }, /*#__PURE__*/React.createElement("stop", {
      offset: "0%",
      stopColor: "var(--color-primary)",
      stopOpacity: "0.25"
    }), /*#__PURE__*/React.createElement("stop", {
      offset: "100%",
      stopColor: "var(--color-primary)",
      stopOpacity: "0"
    }))), /*#__PURE__*/React.createElement("path", {
      d: area,
      fill: "url(#arad-spark)"
    }), /*#__PURE__*/React.createElement("path", {
      d: d,
      fill: "none",
      stroke: "var(--color-primary)",
      strokeWidth: "1.5"
    }));
  }
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      padding: 'var(--space-5)',
      boxShadow: 'var(--shadow-sm)',
      minHeight: 110,
      boxSizing: 'border-box',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      fontWeight: 'var(--weight-semibold)',
      letterSpacing: 'var(--tracking-caps)',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: '12px'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-kpi)',
      fontWeight: 'var(--weight-semibold)',
      color: 'var(--color-text)',
      lineHeight: 1,
      letterSpacing: 'var(--tracking-tight)'
    }
  }, value, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '16px',
      color: 'var(--color-text-secondary)',
      marginLeft: 2
    }
  }, unit)), subtitle && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: '12px',
      fontWeight: 'var(--weight-medium)',
      color: sc,
      marginTop: '10px'
    }
  }, subtitle), sparkEl);
}
Object.assign(__ds_scope, { KPICard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/KPICard.jsx", error: String((e && e.message) || e) }); }

// components/data/MetricPill.jsx
try { (() => {
/**
 * Small metric pill — monospace value over a caps label. Used in result
 * rows (%GR&R | EV | AV | NDC). tone optionally colors the value.
 */
function MetricPill({
  value,
  label,
  tone = 'default',
  style = {}
}) {
  const toneColors = {
    default: 'var(--color-text)',
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    info: 'var(--color-primary)'
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 96,
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: '12px 14px',
      boxSizing: 'border-box',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: '20px',
      fontWeight: 'var(--weight-semibold)',
      color: toneColors[tone] || toneColors.default,
      lineHeight: 1.1
    }
  }, value), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      letterSpacing: 'var(--tracking-caps)',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginTop: '6px'
    }
  }, label));
}
Object.assign(__ds_scope, { MetricPill });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/MetricPill.jsx", error: String((e && e.message) || e) }); }

// components/data/SegmentedBar.jsx
try { (() => {
/**
 * Horizontal stacked bar for variance decomposition (EV% / AV% / PV%) or any
 * part-to-whole breakdown. Pass `segments` as [{label, value, color}].
 */
function SegmentedBar({
  segments = [],
  height = 28,
  showLabels = true,
  style = {}
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const palette = ['var(--color-primary)', 'var(--color-secondary)', 'var(--color-success)', 'var(--color-warning)'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      height,
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
      border: '1px solid var(--color-border)'
    }
  }, segments.map((s, i) => {
    const pct = s.value / total * 100;
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      title: `${s.label}: ${s.value}%`,
      style: {
        width: `${pct}%`,
        background: s.color || palette[i % palette.length],
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-caption)',
        fontWeight: 'var(--weight-semibold)',
        color: 'rgba(255,255,255,0.92)',
        transition: 'width 400ms var(--ease-out)'
      }
    }, pct > 10 ? `${s.value}%` : '');
  })), showLabels && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: '16px',
      marginTop: '10px',
      flexWrap: 'wrap'
    }
  }, segments.map((s, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      color: 'var(--color-text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 8,
      borderRadius: 2,
      background: s.color || palette[i % palette.length]
    }
  }), s.label, " ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, s.value, "%")))));
}
Object.assign(__ds_scope, { SegmentedBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/SegmentedBar.jsx", error: String((e && e.message) || e) }); }

// components/feedback/ProgressBar.jsx
try { (() => {
/**
 * Thin progress / budget bar with optional value + max labels.
 * tone colors the fill; over-threshold can be flagged by passing tone="warning".
 */
function ProgressBar({
  value = 0,
  max = 100,
  tone = 'info',
  label = null,
  valueLabel = null,
  height = 6,
  style = {}
}) {
  const pct = Math.max(0, Math.min(100, value / max * 100));
  const colors = {
    info: 'var(--color-primary)',
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    ai: 'var(--color-secondary)'
  };
  const c = colors[tone] || colors.info;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      ...style
    }
  }, (label || valueLabel) && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: '6px'
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      color: 'var(--color-text-secondary)'
    }
  }, label), valueLabel && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-caption)',
      color: 'var(--color-text)'
    }
  }, valueLabel)), /*#__PURE__*/React.createElement("div", {
    style: {
      height,
      background: 'var(--color-surface-inset)',
      borderRadius: 'var(--radius-full)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${pct}%`,
      height: '100%',
      borderRadius: 'var(--radius-full)',
      background: `linear-gradient(90deg, ${c}, ${c})`,
      boxShadow: `0 0 8px ${c}`,
      transition: 'width 400ms var(--ease-out)'
    }
  })));
}
Object.assign(__ds_scope, { ProgressBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/ProgressBar.jsx", error: String((e && e.message) || e) }); }

// components/feedback/StatusDot.jsx
try { (() => {
/**
 * Live status indicator — a colored dot with an optional animated pulse ring.
 * Used for "Live" connection states and active-severity markers.
 */
function StatusDot({
  tone = 'success',
  pulse = true,
  size = 8,
  label = null,
  style = {}
}) {
  const colors = {
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    info: 'var(--color-primary)',
    purple: 'var(--color-secondary)',
    muted: 'var(--color-text-muted)'
  };
  const c = colors[tone] || colors.success;
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative',
      width: size,
      height: size,
      display: 'inline-block'
    }
  }, pulse && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: '50%',
      background: c,
      animation: 'arad-pulse-ring 1.8s var(--ease-out) infinite'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: '50%',
      background: c,
      boxShadow: `0 0 6px ${c}`
    }
  }), /*#__PURE__*/React.createElement("style", null, `@keyframes arad-pulse-ring{0%{transform:scale(1);opacity:.6}70%{transform:scale(2.6);opacity:0}100%{opacity:0}}`)), label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-caption)',
      fontWeight: 'var(--weight-semibold)',
      color: 'var(--color-text-secondary)',
      letterSpacing: '0.02em'
    }
  }, label));
}
Object.assign(__ds_scope, { StatusDot });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/StatusDot.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/Alerts.jsx
try { (() => {
/* Arad UI Kit — Alerts page (severity-coded feed + accuracy tracker). */

const ALERTS = [{
  sev: 'critical',
  rule: 'Nelson Rule 1',
  part: 'PN-4821',
  eq: 'CMM-001',
  char: 'Bore Diameter',
  val: 10.042,
  limit: 'UCL 10.030',
  ago: '2 min ago',
  state: 'open'
}, {
  sev: 'critical',
  rule: 'Nelson Rule 1',
  part: 'PN-3390',
  eq: 'CMM-002',
  char: 'Hole Position',
  val: 0.214,
  limit: 'UCL 0.200',
  ago: '11 min ago',
  state: 'open'
}, {
  sev: 'warning',
  rule: 'Nelson Rule 3',
  part: 'PN-4821',
  eq: 'CMM-001',
  char: 'Bore Diameter',
  val: null,
  limit: '6 pts trending up',
  ago: '18 min ago',
  state: 'confirmed'
}, {
  sev: 'warning',
  rule: 'Nelson Rule 2',
  part: 'PN-7755',
  eq: 'OPT-204',
  char: 'Surface Flatness',
  val: null,
  limit: '9 pts one side of CL',
  ago: '34 min ago',
  state: 'open'
}, {
  sev: 'info',
  rule: 'Nelson Rule 5',
  part: 'PN-1120',
  eq: 'LMS-07',
  char: 'Roundness',
  val: null,
  limit: '2 of 3 near 2σ',
  ago: '1 hr ago',
  state: 'false'
}];
const sevConf = {
  critical: {
    border: '#EF4444',
    tone: 'critical',
    label: 'Critical'
  },
  warning: {
    border: '#F59E0B',
    tone: 'conditional',
    label: 'High'
  },
  info: {
    border: '#3B82F6',
    tone: 'info',
    label: 'Medium'
  }
};
function AlertCard({
  a
}) {
  const c = sevConf[a.sev];
  const dim = a.state === 'false';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderLeft: `3px solid ${a.state === 'confirmed' ? 'var(--color-success)' : c.border}`,
      borderRadius: 'var(--radius-md)',
      padding: '14px 18px',
      opacity: dim ? 0.5 : 1,
      transition: 'opacity var(--transition)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      marginBottom: 8,
      flexWrap: 'wrap'
    }
  }, a.state === 'confirmed' ? /*#__PURE__*/React.createElement(StatusDot, {
    tone: "success",
    pulse: false,
    size: 7
  }) : a.sev === 'critical' ? /*#__PURE__*/React.createElement(StatusDot, {
    tone: "critical",
    size: 7
  }) : /*#__PURE__*/React.createElement(StatusDot, {
    tone: a.sev === 'warning' ? 'warning' : 'info',
    pulse: false,
    size: 7
  }), /*#__PURE__*/React.createElement(Badge, {
    tone: c.tone
  }, c.label), /*#__PURE__*/React.createElement(Badge, {
    tone: "neutral",
    variant: "outline"
  }, a.rule), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
      color: 'var(--color-text-secondary)'
    }
  }, a.part, " \xB7 ", a.eq), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), a.state === 'confirmed' && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 600,
      color: 'var(--color-success)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Check",
    size: 14,
    color: "var(--color-success)"
  }), "Confirmed")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text)',
      marginBottom: 4
    }
  }, a.char, " ", a.val != null ? /*#__PURE__*/React.createElement(React.Fragment, null, "exceeded limit: ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-critical)',
      fontWeight: 600
    }
  }, a.val), " vs ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text-secondary)'
    }
  }, a.limit)) : /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-text-secondary)'
    }
  }, a.limit)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      color: 'var(--color-text-muted)'
    }
  }, a.ago), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), a.state === 'open' && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "sm",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "Check",
      size: 13
    })
  }, "Confirm"), /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    size: "sm",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "X",
      size: 14
    })
  }))));
}
function Alerts() {
  const [filter, setFilter] = useState('All');
  const filters = ['All', 'Critical', 'High', 'Medium', 'Low'];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(PageHeader, {
    title: "Alert Feed",
    actions: /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 12px',
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "Activity",
      size: 14,
      color: "var(--color-success)"
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-sans)',
        fontSize: 12,
        color: 'var(--color-text-secondary)'
      }
    }, "Alert Accuracy"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 13,
        fontWeight: 600,
        color: 'var(--color-success)'
      }
    }, "97.3%"))
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6,
      marginBottom: 16
    }
  }, filters.map(f => /*#__PURE__*/React.createElement("button", {
    key: f,
    onClick: () => setFilter(f),
    style: {
      height: 30,
      padding: '0 14px',
      borderRadius: 999,
      cursor: 'pointer',
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 500,
      border: `1px solid ${filter === f ? 'var(--color-primary)' : 'var(--color-border)'}`,
      background: filter === f ? 'var(--color-primary-soft)' : 'transparent',
      color: filter === f ? 'var(--color-primary)' : 'var(--color-text-secondary)'
    }
  }, f))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 280px',
      gap: 16,
      alignItems: 'start'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10
    }
  }, ALERTS.map((a, i) => /*#__PURE__*/React.createElement(AlertCard, {
    key: i,
    a: a
  }))), /*#__PURE__*/React.createElement(Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: '0 0 16px',
      fontFamily: 'var(--font-sans)',
      fontSize: 14,
      fontWeight: 600
    }
  }, "Accuracy Tracker"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 32,
      fontWeight: 600,
      color: 'var(--color-success)',
      lineHeight: 1
    }
  }, "97.3%"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      color: 'var(--color-text-muted)',
      marginTop: 4
    }
  }, "Last 30 days"), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 1,
      background: 'var(--color-border)',
      margin: '16px 0'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontFamily: 'var(--font-sans)',
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-text-secondary)'
    }
  }, "True positives"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-success)',
      fontWeight: 600
    }
  }, "284")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontFamily: 'var(--font-sans)',
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-text-secondary)'
    }
  }, "False positives"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-critical)',
      fontWeight: 600
    }
  }, "8"))), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: '18px 0 8px',
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-muted)'
    }
  }, "7-day rolling accuracy"), /*#__PURE__*/React.createElement(Sparkline, {
    data: [95.8, 96.1, 96.4, 96.0, 96.9, 97.1, 97.3],
    w: 228,
    h: 48,
    color: "var(--color-success)",
    id: "acc"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 16,
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '6px 12px',
      borderRadius: 999,
      background: 'var(--color-pass-bg)',
      width: '100%',
      boxSizing: 'border-box',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Check",
    size: 14,
    color: "var(--color-pass-text)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 600,
      color: 'var(--color-pass-text)'
    }
  }, "On Track vs 95% target")))));
}
Object.assign(window, {
  Alerts
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/Alerts.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/Assistant.jsx
try { (() => {
/* Arad UI Kit — AI Assistant (full-page chat). */

const SUGGESTED = ['Why is CMM-001 failing?', 'Show me trends this week', 'Which equipment needs review?'];
const CANNED = {
  default: {
    text: "Here's what I'm seeing across your quality data right now:",
    blocks: [{
      h: 'Open SPC violations',
      items: ['CMM-001 · Bore Diameter — 3 points above UCL (Rule 1)', 'CMM-002 · Hole Position — 1 point above UCL (Rule 1)']
    }, {
      h: 'Recommendation',
      p: 'Prioritize CMM-001 — the upward drift suggests progressive tool wear. Halt the run before the next lot.'
    }]
  },
  'Why is CMM-001 failing?': {
    text: 'CMM-001 has the highest open risk on the floor. Breakdown:',
    blocks: [{
      h: 'Signal',
      items: ['3 points breaching UCL (10.030) over the last 8 subgroups', 'Latest reading 10.042 — 0.012 above the limit', 'Most recent GR&R: %GR&R 23.4%, NDC 4 (Conditional)']
    }, {
      h: 'Likely cause',
      p: 'Repeatability (EV 18.1%) dominates the gauge error, and the trend is monotonic upward — classic progressive boring-tool wear rather than operator variation.'
    }, {
      h: 'Next step',
      p: 'Re-seat the touch probe stylus and verify the tool offset, then re-run a short confirmation study.'
    }]
  }
};
function TypingDots() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 4,
      padding: '4px 0'
    }
  }, [0, 1, 2].map(i => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      width: 6,
      height: 6,
      borderRadius: 999,
      background: 'var(--color-secondary)',
      animation: `arad-typing 1.2s ${i * 0.15}s infinite`
    }
  })), /*#__PURE__*/React.createElement("style", null, `@keyframes arad-typing{0%,60%,100%{opacity:.25;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}`));
}
function AIMessage({
  data,
  typing
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 12,
      maxWidth: '78%'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 30,
      height: 30,
      borderRadius: 8,
      background: 'var(--color-surface-elevated)',
      border: '1px solid var(--color-border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Sparkles",
    size: 15,
    color: "var(--color-secondary)"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      borderLeft: '3px solid var(--color-secondary)',
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderLeft: '3px solid var(--color-secondary)',
      borderRadius: '0 var(--radius-lg) var(--radius-lg) var(--radius-lg)',
      padding: '14px 16px'
    }
  }, typing ? /*#__PURE__*/React.createElement(TypingDots, null) : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: '0 0 12px',
      fontFamily: 'var(--font-sans)',
      fontSize: 13.5,
      lineHeight: 1.55,
      color: 'var(--color-text)'
    }
  }, data.text), data.blocks.map((b, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      marginBottom: i < data.blocks.length - 1 ? 12 : 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.06em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 6
    }
  }, b.h), b.items ? /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      paddingLeft: 0,
      listStyle: 'none',
      display: 'flex',
      flexDirection: 'column',
      gap: 6
    }
  }, b.items.map((it, j) => /*#__PURE__*/React.createElement("li", {
    key: j,
    style: {
      display: 'flex',
      gap: 8,
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      lineHeight: 1.5,
      color: 'var(--color-text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-secondary)',
      flex: 'none'
    }
  }, "\u25B8"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: /[0-9]/.test(it) ? 'var(--font-sans)' : 'inherit'
    }
  }, it)))) : /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      lineHeight: 1.55,
      color: 'var(--color-text-secondary)'
    }
  }, b.p))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10,
      fontFamily: 'var(--font-mono)',
      fontSize: 10,
      color: 'var(--color-text-muted)'
    }
  }, "14:33:12"))));
}
function UserMessage({
  text
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      alignSelf: 'flex-end',
      maxWidth: '70%'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'linear-gradient(180deg, #1E3A8A, #1E40AF)',
      border: '1px solid rgba(59,130,246,.4)',
      borderRadius: 'var(--radius-lg) 0 var(--radius-lg) var(--radius-lg)',
      padding: '12px 16px',
      fontFamily: 'var(--font-sans)',
      fontSize: 13.5,
      color: '#fff',
      lineHeight: 1.5
    }
  }, text), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'right',
      marginTop: 4,
      fontFamily: 'var(--font-mono)',
      fontSize: 10,
      color: 'var(--color-text-muted)'
    }
  }, "14:33:08"));
}
function ContextCard({
  icon,
  label,
  value
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: 12,
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: icon,
    size: 16,
    color: "var(--color-text-muted)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      color: 'var(--color-text-secondary)'
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 14,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, value));
}
function Assistant() {
  const [messages, setMessages] = useState([{
    role: 'user',
    text: 'Give me a status check on the floor.'
  }, {
    role: 'ai',
    data: CANNED.default
  }]);
  const [typing, setTyping] = useState(false);
  const [input, setInput] = useState('');
  const [chips, setChips] = useState(['GR&R Studies', 'SPC Violations']);
  const scrollRef = useRef(null);
  const send = text => {
    if (!text.trim()) return;
    setInput('');
    setMessages(m => [...m, {
      role: 'user',
      text
    }]);
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMessages(m => [...m, {
        role: 'ai',
        data: CANNED[text] || CANNED.default
      }]);
    }, 1300);
  };
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, typing]);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      height: '100%',
      minHeight: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 280,
      flex: 'none',
      borderRight: '1px solid var(--color-border)',
      background: 'var(--color-surface)',
      padding: 20,
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
      overflowY: 'auto'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)'
    }
  }, "System Context"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement(ContextCard, {
    icon: "ChartColumn",
    label: "Recent GR&R",
    value: "12"
  }), /*#__PURE__*/React.createElement(ContextCard, {
    icon: "TriangleAlert",
    label: "Open Violations",
    value: "3"
  }), /*#__PURE__*/React.createElement(ContextCard, {
    icon: "ClipboardCheck",
    label: "Pending Reviews",
    value: "4"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginTop: 4
    }
  }, "Suggested"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, SUGGESTED.map(q => /*#__PURE__*/React.createElement("button", {
    key: q,
    onClick: () => send(q),
    style: {
      textAlign: 'left',
      padding: '10px 12px',
      background: 'transparent',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      cursor: 'pointer',
      fontFamily: 'var(--font-sans)',
      fontSize: 12.5,
      color: 'var(--color-text-secondary)',
      transition: 'all var(--transition)'
    },
    onMouseEnter: e => {
      e.currentTarget.style.borderColor = 'var(--color-secondary)';
      e.currentTarget.style.color = 'var(--color-text)';
    },
    onMouseLeave: e => {
      e.currentTarget.style.borderColor = 'var(--color-border)';
      e.currentTarget.style.color = 'var(--color-text-secondary)';
    }
  }, q)))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    ref: scrollRef,
    style: {
      flex: 1,
      overflowY: 'auto',
      padding: '28px 32px',
      display: 'flex',
      flexDirection: 'column',
      gap: 20
    }
  }, messages.map((m, i) => m.role === 'user' ? /*#__PURE__*/React.createElement(UserMessage, {
    key: i,
    text: m.text
  }) : /*#__PURE__*/React.createElement(AIMessage, {
    key: i,
    data: m.data
  })), typing && /*#__PURE__*/React.createElement(AIMessage, {
    typing: true,
    data: {}
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: '1px solid var(--color-border)',
      padding: '16px 32px 12px',
      background: 'var(--color-surface)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginBottom: 10,
      flexWrap: 'wrap'
    }
  }, chips.map(c => /*#__PURE__*/React.createElement("span", {
    key: c,
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '4px 8px 4px 10px',
      background: 'var(--color-secondary-soft)',
      border: '1px solid rgba(99,102,241,.35)',
      borderRadius: 999,
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 500,
      color: 'var(--color-purple-text)'
    }
  }, c, /*#__PURE__*/React.createElement("button", {
    onClick: () => setChips(cs => cs.filter(x => x !== c)),
    style: {
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      display: 'flex',
      padding: 0,
      color: 'var(--color-purple-text)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "X",
    size: 12
  }))))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      alignItems: 'flex-end'
    }
  }, /*#__PURE__*/React.createElement("textarea", {
    value: input,
    onChange: e => setInput(e.target.value),
    onKeyDown: e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send(input);
      }
    },
    placeholder: "Ask about quality data\u2026",
    rows: 1,
    style: {
      flex: 1,
      resize: 'none',
      padding: '12px 14px',
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      color: 'var(--color-text)',
      fontFamily: 'var(--font-sans)',
      fontSize: 13.5,
      outline: 'none',
      maxHeight: 120,
      boxSizing: 'border-box'
    },
    onFocus: e => {
      e.target.style.borderColor = 'var(--color-primary)';
      e.target.style.boxShadow = 'var(--ring-focus)';
    },
    onBlur: e => {
      e.target.style.borderColor = 'var(--color-border)';
      e.target.style.boxShadow = 'none';
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: () => send(input),
    style: {
      width: 44,
      height: 44,
      flex: 'none',
      borderRadius: 'var(--radius-md)',
      border: 'none',
      cursor: 'pointer',
      background: 'linear-gradient(180deg,#3B82F6,#2563EB)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "ArrowUp",
    size: 18,
    color: "#fff"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      marginTop: 8,
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Sparkles",
    size: 11,
    color: "var(--color-text-muted)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 10,
      color: 'var(--color-text-muted)'
    }
  }, "Powered by Gemini \xB7 responses may be inexact")))));
}
Object.assign(window, {
  Assistant
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/Assistant.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/Dashboard.jsx
try { (() => {
/* Arad UI Kit — Dashboard page. */

const SPC_DATA = [{
  v: 10.012
}, {
  v: 10.018
}, {
  v: 10.009
}, {
  v: 10.021
}, {
  v: 10.015
}, {
  v: 10.024
}, {
  v: 10.019
}, {
  v: 10.028
}, {
  v: 10.022
}, {
  v: 10.031
}, {
  v: 10.026
}, {
  v: 10.034,
  violation: true
}, {
  v: 10.029
}, {
  v: 10.023
}, {
  v: 10.038,
  violation: true
}, {
  v: 10.027
}, {
  v: 10.020
}, {
  v: 10.025
}, {
  v: 10.030
}, {
  v: 10.042,
  violation: true
}];
const EVENTS = [{
  t: '14:32:08',
  type: 'spc.violation',
  tone: 'fail',
  text: 'PN-4821 · Bore Ø exceeded UCL on CMM-001'
}, {
  t: '14:28:51',
  type: 'grr.complete',
  tone: 'info',
  text: 'Study #2471 complete — %GR&R 8.2%, Pass'
}, {
  t: '14:21:30',
  type: 'alert.sent',
  tone: 'conditional',
  text: 'Alert dispatched to QA team (Rule 3)'
}, {
  t: '14:15:02',
  type: 'review.required',
  tone: 'purple',
  text: 'Gauge G-118 flagged for manager review'
}, {
  t: '14:09:44',
  type: 'grr.complete',
  tone: 'info',
  text: 'Study #2470 complete — %GR&R 23.4%, Conditional'
}, {
  t: '13:58:12',
  type: 'spc.violation',
  tone: 'fail',
  text: 'PN-3390 · Wall thickness run of 7 above CL'
}, {
  t: '13:47:05',
  type: 'alert.sent',
  tone: 'conditional',
  text: 'Alert dispatched to QA team (Rule 1)'
}];
const PENDING = [{
  eq: 'CMM-001',
  grr: 23.4,
  days: 2
}, {
  eq: 'G-118',
  grr: 31.7,
  days: 4
}, {
  eq: 'OPT-204',
  grr: 12.1,
  days: 1
}];
function SectionTitle({
  children,
  right
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      fontFamily: 'var(--font-sans)',
      fontSize: 15,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, children), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), right);
}
function Dashboard() {
  const [animKey, setAnimKey] = useState(0);
  const [aiOpen, setAiOpen] = useState(true);
  useEffect(() => {
    setAnimKey(k => k + 1);
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4,1fr)',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(KPICard, {
    id: "k1",
    label: "GR&R Studies",
    value: "247",
    subtitle: "+12 this week",
    subtitleTone: "success",
    spark: [230, 233, 235, 232, 240, 244, 247],
    animateKey: animKey
  }), /*#__PURE__*/React.createElement(KPICard, {
    id: "k2",
    label: "Alert Accuracy",
    value: "97.3",
    unit: "%",
    subtitle: "\u25B2 vs 95% SLA",
    subtitleTone: "success",
    spark: [95.1, 95.4, 96, 96.2, 96.8, 97, 97.3],
    animateKey: animKey
  }), /*#__PURE__*/React.createElement(KPICard, {
    id: "k3",
    label: "Active Alerts",
    value: "3",
    subtitle: "critical \xB7 12 total",
    subtitleTone: "critical",
    spark: [6, 5, 7, 4, 5, 4, 3],
    animateKey: animKey
  }), /*#__PURE__*/React.createElement(KPICard, {
    id: "k4",
    label: "Avg Study Time",
    value: "1.2",
    unit: "hrs",
    subtitle: "\u2713 under 2hr SLA",
    subtitleTone: "success",
    spark: [1.6, 1.5, 1.4, 1.5, 1.3, 1.3, 1.2],
    animateKey: animKey
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1.5fr 1fr',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(SectionTitle, {
    right: /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        height: 28,
        padding: '0 10px',
        background: 'var(--color-surface-inset)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        color: 'var(--color-text)'
      }
    }, "PN-4821 ", /*#__PURE__*/React.createElement(Icon, {
      name: "ChevronRight",
      size: 12,
      color: "var(--color-text-muted)",
      style: {
        transform: 'rotate(90deg)'
      }
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        height: 28,
        padding: '0 10px',
        background: 'var(--color-surface-inset)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        color: 'var(--color-text)'
      }
    }, "Bore \xD8 ", /*#__PURE__*/React.createElement(Icon, {
      name: "ChevronRight",
      size: 12,
      color: "var(--color-text-muted)",
      style: {
        transform: 'rotate(90deg)'
      }
    })))
  }, "Live Process Monitor"), /*#__PURE__*/React.createElement(SPCChart, {
    data: SPC_DATA,
    ucl: 10.030,
    cl: 10.020,
    lcl: 10.010
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginTop: 14,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement(Badge, {
    tone: "fail",
    variant: "outline"
  }, "Rule 1 \xB7 2 violations"), /*#__PURE__*/React.createElement(Badge, {
    tone: "conditional",
    variant: "outline"
  }, "Rule 3 \xB7 1 violation")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 16,
      borderLeft: '3px solid var(--color-secondary)',
      background: 'var(--color-surface-inset)',
      borderRadius: '0 var(--radius-md) var(--radius-md) 0',
      padding: 14
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setAiOpen(o => !o),
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      width: '100%',
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      padding: 0
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Sparkles",
    size: 15,
    color: "var(--color-secondary)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, "AI Interpretation"), /*#__PURE__*/React.createElement(Badge, {
    tone: "critical"
  }, "Urgent"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement(Icon, {
    name: "ChevronRight",
    size: 16,
    color: "var(--color-text-muted)",
    style: {
      transform: aiOpen ? 'rotate(90deg)' : 'none',
      transition: 'transform var(--transition)'
    }
  })), aiOpen && /*#__PURE__*/React.createElement("p", {
    style: {
      margin: '10px 0 0',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      lineHeight: 1.55,
      color: 'var(--color-text-secondary)'
    }
  }, "Three points breach the upper control limit with an upward drift over the last 8 subgroups \u2014 consistent with progressive tool wear on ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, "CMM-001"), ". Recommend halting the run and verifying the boring tool offset before the next lot."))), /*#__PURE__*/React.createElement(Card, {
    padding: 0,
    style: {
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 20px',
      borderBottom: '1px solid var(--color-border)',
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      fontFamily: 'var(--font-sans)',
      fontSize: 15,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, "Live Events"), /*#__PURE__*/React.createElement(StatusDot, {
    tone: "success"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: 'auto',
      maxHeight: 420
    }
  }, EVENTS.map((e, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      gap: 10,
      padding: '12px 20px',
      borderBottom: '1px solid var(--color-border)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      color: 'var(--color-text-muted)',
      flex: 'none',
      paddingTop: 2
    }
  }, e.t), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Badge, {
    tone: e.tone,
    style: {
      marginBottom: 6
    }
  }, e.type), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      color: 'var(--color-text-secondary)',
      lineHeight: 1.45
    }
  }, e.text))))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '10px 20px',
      borderTop: '1px solid var(--color-border)',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      color: 'var(--color-text-muted)'
    }
  }, /*#__PURE__*/React.createElement(StatusDot, {
    tone: "success",
    size: 6
  }), " WebSocket connected \xB7 7 events/min"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3,1fr)',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(SectionTitle, {
    right: /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        fontWeight: 600,
        color: 'var(--color-primary)',
        background: 'var(--color-primary-soft)',
        padding: '2px 8px',
        borderRadius: 999
      }
    }, "14")
  }, "Pending Reviews"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10
    }
  }, PENDING.map((p, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      paddingBottom: 10,
      borderBottom: i < PENDING.length - 1 ? '1px solid var(--color-border)' : 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 13,
      color: 'var(--color-text)'
    }
  }, p.eq), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-muted)',
      marginTop: 2
    }
  }, "%GR&R ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: p.grr > 30 ? 'var(--color-critical)' : p.grr > 10 ? 'var(--color-warning)' : 'var(--color-success)'
    }
  }, p.grr, "%"), " \xB7 ", p.days, "d pending")), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "sm"
  }, "Review")))), /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      display: 'inline-block',
      marginTop: 12,
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      color: 'var(--color-primary)',
      textDecoration: 'none'
    }
  }, "View all 14 \u2192")), /*#__PURE__*/React.createElement(Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "Alert Accuracy"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(DonutGauge, {
    value: 97.3,
    target: 95
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Check",
    size: 14,
    color: "var(--color-success)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 600,
      color: 'var(--color-success)'
    }
  }, "Target Met (95%)")), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-muted)'
    }
  }, "Last 30 days"))), /*#__PURE__*/React.createElement(Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "AI Spend"), /*#__PURE__*/React.createElement(ProgressBar, {
    value: 8.4,
    max: 50,
    tone: "info",
    valueLabel: "$8.40 / $50.00"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: '14px 0',
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, [['GR&R narratives', '$4.10'], ['SPC interpret', '$2.85'], ['Chat', '$1.45']].map(([k, v]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      color: 'var(--color-text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("span", null, k), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, v)))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-muted)',
      marginBottom: 8
    }
  }, "Daily usage \xB7 last 7 days"), /*#__PURE__*/React.createElement(MiniBars, {
    data: [0.9, 1.2, 0.7, 1.5, 1.1, 1.0, 1.4]
  }))));
}
Object.assign(window, {
  Dashboard
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/Dashboard.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/GRRStudies.jsx
try { (() => {
/* Arad UI Kit — GR&R Studies page (submit form + AI-narrated results + history). */

const GRR_HISTORY = [{
  date: '2026-06-08',
  eq: 'CMM-001',
  char: 'Bore Diameter',
  grr: 23.4,
  ndc: 4,
  verdict: 'conditional'
}, {
  date: '2026-06-07',
  eq: 'OPT-204',
  char: 'Surface Flatness',
  grr: 8.2,
  ndc: 9,
  verdict: 'pass'
}, {
  date: '2026-06-06',
  eq: 'G-118',
  char: 'Thread Pitch',
  grr: 31.7,
  ndc: 2,
  verdict: 'fail'
}, {
  date: '2026-06-05',
  eq: 'CMM-002',
  char: 'Wall Thickness',
  grr: 9.1,
  ndc: 7,
  verdict: 'pass'
}, {
  date: '2026-06-04',
  eq: 'LMS-07',
  char: 'Bore Diameter',
  grr: 14.6,
  ndc: 5,
  verdict: 'conditional'
}];
function StepDots({
  step
}) {
  const steps = ['Setup', 'Data', 'Run'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, steps.map((s, i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: s
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 20,
      height: 20,
      borderRadius: 999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      fontWeight: 600,
      background: i + 1 <= step ? 'var(--color-primary)' : 'var(--color-surface-inset)',
      color: i + 1 <= step ? '#fff' : 'var(--color-text-muted)',
      border: i + 1 <= step ? 'none' : '1px solid var(--color-border)'
    }
  }, i + 1), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 500,
      color: i + 1 <= step ? 'var(--color-text)' : 'var(--color-text-muted)'
    }
  }, s)), i < steps.length - 1 && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 16,
      height: 1,
      background: 'var(--color-border)'
    }
  }))));
}
function VerdictBadge({
  v
}) {
  const map = {
    pass: ['pass', 'Pass'],
    conditional: ['conditional', 'Conditional'],
    fail: ['fail', 'Fail']
  };
  const [tone, label] = map[v];
  return /*#__PURE__*/React.createElement(Badge, {
    tone: tone
  }, label);
}
function EmptyResults() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 18,
      padding: 40,
      minHeight: 360,
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "120",
    height: "104",
    viewBox: "0 0 120 104",
    fill: "none",
    style: {
      opacity: 0.5
    }
  }, /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("linearGradient", {
    id: "hexEmpty",
    x1: "0",
    y1: "0",
    x2: "120",
    y2: "104"
  }, /*#__PURE__*/React.createElement("stop", {
    stopColor: "#6366F1"
  }), /*#__PURE__*/React.createElement("stop", {
    offset: "1",
    stopColor: "#3B82F6"
  }))), [[30, 26], [60, 9], [90, 26], [30, 60], [60, 43], [90, 60], [60, 77]].map(([cx, cy], i) => /*#__PURE__*/React.createElement("path", {
    key: i,
    d: `M${cx} ${cy - 14}l12 7v14l-12 7-12-7V${cy - 7}z`,
    stroke: "url(#hexEmpty)",
    strokeWidth: "1.4",
    fill: "url(#hexEmpty)",
    fillOpacity: i === 3 ? 0.18 : 0.04
  }))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 15,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, "No results yet"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text-secondary)',
      marginTop: 6,
      maxWidth: 320
    }
  }, "Submit your first study to see acceptance verdict, variance decomposition, and an AI narrative here.")));
}
function PopulatedResults() {
  const [checks, setChecks] = useState([false, false, false]);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 18
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      padding: '16px 20px',
      borderRadius: 'var(--radius-lg)',
      background: 'linear-gradient(135deg, rgba(245,158,11,.16), rgba(245,158,11,.04))',
      border: '1px solid rgba(245,158,11,.3)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 44,
      height: 44,
      borderRadius: 'var(--radius-md)',
      background: 'rgba(245,158,11,.15)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "TriangleAlert",
    size: 22,
    color: "var(--color-warning)"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 18,
      fontWeight: 700,
      color: 'var(--color-cond-text)'
    }
  }, "Conditional"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text-secondary)'
    }
  }, "Requires manager review before acceptance"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(MetricPill, {
    value: "23.4%",
    label: "%GR&R",
    tone: "warning"
  }), /*#__PURE__*/React.createElement(MetricPill, {
    value: "18.1%",
    label: "EV \xB7 Repeat."
  }), /*#__PURE__*/React.createElement(MetricPill, {
    value: "14.8%",
    label: "AV \xB7 Reprod."
  }), /*#__PURE__*/React.createElement(MetricPill, {
    value: "4",
    label: "NDC",
    tone: "warning"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 600,
      letterSpacing: '.04em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 10
    }
  }, "Variance Decomposition"), /*#__PURE__*/React.createElement(SegmentedBar, {
    segments: [{
      label: 'EV (Repeatability)',
      value: 42
    }, {
      label: 'AV (Reproducibility)',
      value: 23
    }, {
      label: 'PV (Part)',
      value: 35
    }]
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      borderLeft: '3px solid var(--color-secondary)',
      background: 'var(--color-surface-inset)',
      borderRadius: '0 var(--radius-lg) var(--radius-lg) 0',
      padding: 18
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      marginBottom: 12
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Sparkles",
    size: 16,
    color: "var(--color-secondary)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 14,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, "AI Analysis"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement(Badge, {
    tone: "conditional"
  }, "Risk: Medium"), /*#__PURE__*/React.createElement(Badge, {
    tone: "neutral",
    variant: "outline"
  }, "Confidence 91%")), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: '0 0 14px',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      lineHeight: 1.6,
      color: 'var(--color-text-secondary)'
    }
  }, "The measurement system explains ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, "23.4%"), " of total variation \u2014 above the 10% target but below the 30% rejection threshold. Repeatability (gauge) dominates the error, suggesting the instrument rather than the operators is the limiting factor."), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.04em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 6
    }
  }, "Root Cause"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: '0 0 14px',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      lineHeight: 1.6,
      color: 'var(--color-text-secondary)'
    }
  }, "EV at ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, "18.1%"), " points to probe seating repeatability on ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, "CMM-001"), ". NDC of 4 means the gauge resolves only 4 distinct categories across the tolerance."), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.04em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 8
    }
  }, "Recommendations"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, ['Re-qualify the touch probe and re-seat the stylus', 'Add a fixture to constrain part placement on the table', 'Re-run with 3 trials to tighten the EV estimate'].map((rec, i) => /*#__PURE__*/React.createElement("label", {
    key: i,
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: 10,
      cursor: 'pointer'
    }
  }, /*#__PURE__*/React.createElement("span", {
    onClick: () => setChecks(c => c.map((v, j) => j === i ? !v : v)),
    style: {
      width: 18,
      height: 18,
      flex: 'none',
      marginTop: 1,
      borderRadius: 4,
      border: `1px solid ${checks[i] ? 'var(--color-primary)' : 'var(--color-border-strong)'}`,
      background: checks[i] ? 'var(--color-primary)' : 'transparent',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, checks[i] && /*#__PURE__*/React.createElement(Icon, {
    name: "Check",
    size: 13,
    color: "#fff"
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: checks[i] ? 'var(--color-text-muted)' : 'var(--color-text-secondary)',
      textDecoration: checks[i] ? 'line-through' : 'none'
    }
  }, rec))))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "Download",
      size: 15,
      color: "#fff"
    })
  }, "Download PDF Report"), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "ClipboardCheck",
      size: 15
    })
  }, "Add to Review Queue"), /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "Share2",
      size: 15
    })
  }, "Share")));
}
function GRRStudies() {
  const [hasResults, setHasResults] = useState(true);
  const [running, setRunning] = useState(false);
  const [method, setMethod] = useState('Xbar-R');
  const run = () => {
    setRunning(true);
    setTimeout(() => {
      setRunning(false);
      setHasResults(true);
    }, 1600);
  };
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(PageHeader, {
    title: "GR&R Studies",
    subtitle: "Gauge repeatability & reproducibility \u2014 measurement system analysis",
    actions: /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      size: "md",
      onClick: () => setHasResults(h => !h)
    }, hasResults ? 'Show empty state' : 'Show results'), /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      icon: /*#__PURE__*/React.createElement(Icon, {
        name: "Plus",
        size: 15,
        color: "#fff"
      })
    }, "New Study"))
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '0.55fr 1fr',
      gap: 16,
      alignItems: 'start'
    }
  }, /*#__PURE__*/React.createElement(Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 18
    }
  }, /*#__PURE__*/React.createElement(StepDots, {
    step: 1
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 14
    }
  }, /*#__PURE__*/React.createElement(Input, {
    label: "Equipment ID",
    placeholder: "CMM-001",
    defaultValue: "CMM-001"
  }), /*#__PURE__*/React.createElement(Input, {
    label: "Characteristic Name",
    placeholder: "Bore Diameter",
    defaultValue: "Bore Diameter"
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 6
    }
  }, "Method"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: 3
    }
  }, ['Xbar-R', 'ANOVA'].map(m => /*#__PURE__*/React.createElement("button", {
    key: m,
    onClick: () => setMethod(m),
    style: {
      flex: 1,
      height: 30,
      border: 'none',
      borderRadius: 4,
      cursor: 'pointer',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      fontWeight: 500,
      background: method === m ? 'var(--color-surface-elevated)' : 'transparent',
      color: method === m ? 'var(--color-text)' : 'var(--color-text-muted)',
      boxShadow: method === m ? 'var(--shadow-sm)' : 'none'
    }
  }, m)))), /*#__PURE__*/React.createElement(Input, {
    label: "Tolerance (optional)",
    mono: true,
    placeholder: "\xB1 0.025"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1.5px dashed var(--color-border-strong)',
      borderRadius: 'var(--radius-md)',
      padding: 22,
      textAlign: 'center',
      background: 'var(--color-surface-inset)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Upload",
    size: 20,
    color: "var(--color-text-muted)",
    style: {
      margin: '0 auto 8px'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text-secondary)'
    }
  }, "Drop CSV or click to upload"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-muted)',
      marginTop: 4
    }
  }, "or enter data in the grid")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'inline-flex',
      alignSelf: 'flex-start',
      alignItems: 'center',
      gap: 6,
      padding: '6px 10px',
      borderRadius: 'var(--radius-sm)',
      background: 'var(--color-primary-soft)',
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
      color: 'var(--color-primary)'
    }
  }, "3 \xD7 10 \xD7 2 = 60 measurements"), /*#__PURE__*/React.createElement("button", {
    onClick: run,
    disabled: running,
    style: {
      height: 40,
      border: 'none',
      borderRadius: 'var(--radius-md)',
      cursor: running ? 'default' : 'pointer',
      position: 'relative',
      overflow: 'hidden',
      background: 'linear-gradient(180deg,#3B82F6,#2563EB)',
      color: '#fff',
      fontFamily: 'var(--font-sans)',
      fontSize: 14,
      fontWeight: 600,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8
    }
  }, running ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "arad-runbar",
    style: {
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,.25), transparent)',
      backgroundSize: '400px 100%',
      animation: 'arad-shimmer 1s linear infinite'
    }
  }), "Analyzing\u2026") : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Icon, {
    name: "Zap",
    size: 16,
    color: "#fff"
  }), "Run Analysis")))), /*#__PURE__*/React.createElement(Card, {
    padding: hasResults ? 20 : 0,
    style: {
      minHeight: 360,
      display: 'flex',
      flexDirection: 'column'
    }
  }, hasResults ? /*#__PURE__*/React.createElement(PopulatedResults, null) : /*#__PURE__*/React.createElement(EmptyResults, null))), /*#__PURE__*/React.createElement(Card, {
    padding: 0,
    style: {
      marginTop: 16,
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '14px 20px',
      borderBottom: '1px solid var(--color-border)'
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      fontFamily: 'var(--font-sans)',
      fontSize: 14,
      fontWeight: 600
    }
  }, "Study History")), /*#__PURE__*/React.createElement(DataTable, {
    columns: ['Date', 'Equipment', 'Characteristic', '%GR&R', 'NDC', 'Verdict', ''],
    rows: GRR_HISTORY.map(r => [/*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        color: 'var(--color-text-secondary)'
      }
    }, r.date), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)'
      }
    }, r.eq), r.char, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        color: r.grr > 30 ? 'var(--color-critical)' : r.grr > 10 ? 'var(--color-warning)' : 'var(--color-success)'
      }
    }, r.grr, "%"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)'
      }
    }, r.ndc), /*#__PURE__*/React.createElement(VerdictBadge, {
      v: r.verdict
    }), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      size: "sm",
      icon: /*#__PURE__*/React.createElement(Icon, {
        name: "ChevronRight",
        size: 14
      })
    })])
  })));
}

/* Shared table used across pages */
function DataTable({
  columns,
  rows,
  align = []
}) {
  return /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse'
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, columns.map((c, i) => /*#__PURE__*/React.createElement("th", {
    key: i,
    style: {
      textAlign: align[i] || 'left',
      padding: '10px 20px',
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      borderBottom: '1px solid var(--color-border)',
      whiteSpace: 'nowrap'
    }
  }, c)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((row, ri) => /*#__PURE__*/React.createElement("tr", {
    key: ri,
    style: {
      transition: 'background var(--transition)'
    },
    onMouseEnter: e => e.currentTarget.style.background = 'var(--color-surface-hover)',
    onMouseLeave: e => e.currentTarget.style.background = 'transparent'
  }, row.map((cell, ci) => /*#__PURE__*/React.createElement("td", {
    key: ci,
    style: {
      textAlign: align[ci] || 'left',
      padding: '12px 20px',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text)',
      borderBottom: ri < rows.length - 1 ? '1px solid var(--color-border)' : 'none',
      whiteSpace: 'nowrap'
    }
  }, cell))))));
}
Object.assign(window, {
  GRRStudies,
  DataTable,
  VerdictBadge
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/GRRStudies.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/ReviewQueue.jsx
try { (() => {
/* Arad UI Kit — Review Queue page (table + right-side decision drawer). */

const REVIEW_ROWS = [{
  eq: 'CMM-001',
  char: 'Bore Diameter',
  grr: 23.4,
  ndc: 4,
  submitted: '06-08',
  assignee: 'D. Karam',
  due: '06-10',
  status: 'pending',
  overdue: false
}, {
  eq: 'G-118',
  char: 'Thread Pitch',
  grr: 31.7,
  ndc: 2,
  submitted: '06-04',
  assignee: 'M. Reyes',
  due: '06-07',
  status: 'overdue',
  overdue: true
}, {
  eq: 'OPT-204',
  char: 'Surface Flatness',
  grr: 12.1,
  ndc: 5,
  submitted: '06-08',
  assignee: 'D. Karam',
  due: '06-11',
  status: 'pending',
  overdue: false
}, {
  eq: 'LMS-07',
  char: 'Bore Diameter',
  grr: 14.6,
  ndc: 5,
  submitted: '06-05',
  assignee: 'A. Singh',
  due: '06-09',
  status: 'pending',
  overdue: false
}, {
  eq: 'CMM-002',
  char: 'Hole Position',
  grr: 28.9,
  ndc: 3,
  submitted: '06-03',
  assignee: 'M. Reyes',
  due: '06-06',
  status: 'overdue',
  overdue: true
}, {
  eq: 'PRB-12',
  char: 'Roundness',
  grr: 9.8,
  ndc: 8,
  submitted: '06-08',
  assignee: 'A. Singh',
  due: '06-12',
  status: 'pending',
  overdue: false
}];
function grrColor(g) {
  return g > 30 ? 'var(--color-critical)' : g > 10 ? 'var(--color-warning)' : 'var(--color-success)';
}
function ndcTone(n) {
  return n >= 5 ? 'pass' : n >= 2 ? 'conditional' : 'fail';
}
function ReviewDrawer({
  row,
  onClose
}) {
  const [decision, setDecision] = useState('approve');
  if (!row) return null;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      zIndex: 50
    }
  }, /*#__PURE__*/React.createElement("div", {
    onClick: onClose,
    style: {
      position: 'absolute',
      inset: 0,
      background: 'rgba(0,0,8,.55)',
      backdropFilter: 'blur(2px)',
      animation: 'arad-fade-up .2s'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 0,
      right: 0,
      bottom: 0,
      width: 480,
      background: 'var(--color-surface)',
      borderLeft: '1px solid var(--color-border)',
      boxShadow: 'var(--shadow-drawer)',
      display: 'flex',
      flexDirection: 'column',
      animation: 'arad-slide-in .28s var(--ease-out)'
    }
  }, /*#__PURE__*/React.createElement("style", null, `@keyframes arad-slide-in{from{transform:translateX(48px)}to{transform:none}}`), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      padding: '18px 22px',
      borderBottom: '1px solid var(--color-border)'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 16,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, row.eq), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text-secondary)'
    }
  }, row.char)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      width: 32,
      height: 32,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'transparent',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      cursor: 'pointer',
      color: 'var(--color-text-secondary)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "X",
    size: 16
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: 'auto',
      padding: 22,
      display: 'flex',
      flexDirection: 'column',
      gap: 20
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement(MetricPill, {
    value: `${row.grr}%`,
    label: "%GR&R",
    tone: row.grr > 30 ? 'critical' : row.grr > 10 ? 'warning' : 'success'
  }), /*#__PURE__*/React.createElement(MetricPill, {
    value: row.ndc,
    label: "NDC",
    tone: row.ndc >= 5 ? 'success' : row.ndc >= 2 ? 'warning' : 'critical'
  }), /*#__PURE__*/React.createElement(MetricPill, {
    value: row.submitted,
    label: "Submitted"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      borderLeft: '3px solid var(--color-secondary)',
      background: 'var(--color-surface-inset)',
      borderRadius: '0 var(--radius-md) var(--radius-md) 0',
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Sparkles",
    size: 15,
    color: "var(--color-secondary)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      fontWeight: 600
    }
  }, "AI Analysis"), /*#__PURE__*/React.createElement(Badge, {
    tone: row.grr > 30 ? 'fail' : 'conditional',
    style: {
      marginLeft: 'auto'
    }
  }, "Risk: ", row.grr > 30 ? 'High' : 'Medium')), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      lineHeight: 1.6,
      color: 'var(--color-text-secondary)'
    }
  }, "%GR&R of ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, row.grr, "%"), " with NDC ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, row.ndc), ". ", row.grr > 30 ? 'Exceeds the 30% rejection threshold — the gauge cannot reliably discriminate parts. Recommend rejecting and re-qualifying the instrument.' : 'Above the 10% target but acceptable for non-critical characteristics. Manager judgment required.')), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 8
    }
  }, "Decision"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: 3,
      marginBottom: 12
    }
  }, [['approve', 'Approve', 'var(--color-success)'], ['reject', 'Reject', 'var(--color-critical)']].map(([id, label, color]) => /*#__PURE__*/React.createElement("button", {
    key: id,
    onClick: () => setDecision(id),
    style: {
      flex: 1,
      height: 34,
      border: 'none',
      borderRadius: 4,
      cursor: 'pointer',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      fontWeight: 600,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6,
      background: decision === id ? id === 'approve' ? 'rgba(16,185,129,.14)' : 'rgba(239,68,68,.14)' : 'transparent',
      color: decision === id ? color : 'var(--color-text-muted)',
      boxShadow: decision === id ? 'inset 0 0 0 1px ' + color : 'none'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: id === 'approve' ? 'Check' : 'X',
    size: 15
  }), label))), /*#__PURE__*/React.createElement("textarea", {
    placeholder: "Add review notes\u2026",
    rows: 3,
    style: {
      width: '100%',
      padding: 12,
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      color: 'var(--color-text)',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      resize: 'vertical',
      boxSizing: 'border-box',
      outline: 'none'
    }
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 10
    }
  }, "Audit Trail"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10
    }
  }, [['Submitted by system', row.submitted + ' 09:14'], ['Assigned to ' + row.assignee, row.submitted + ' 09:15'], ['AI narrative generated', row.submitted + ' 09:15']].map(([txt, time], i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      gap: 10,
      alignItems: 'baseline'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: 999,
      background: 'var(--color-border-strong)',
      flex: 'none'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      color: 'var(--color-text-secondary)'
    }
  }, txt), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      color: 'var(--color-text-muted)'
    }
  }, time)))))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 18,
      borderTop: '1px solid var(--color-border)',
      display: 'flex',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    onClick: onClose,
    style: {
      flex: 'none'
    }
  }, "Cancel"), /*#__PURE__*/React.createElement(Button, {
    variant: decision === 'reject' ? 'destructive' : 'primary',
    style: {
      flex: 1
    }
  }, "Submit Decision"))));
}
function ReviewQueue() {
  const [tab, setTab] = useState('Pending');
  const [drawer, setDrawer] = useState(null);
  const tabs = ['All', 'Pending', 'Approved', 'Rejected'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      flex: 1
    }
  }, /*#__PURE__*/React.createElement(PageHeader, {
    title: "Review Queue",
    actions: /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        background: 'var(--color-surface-inset)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        padding: 3
      }
    }, tabs.map(t => /*#__PURE__*/React.createElement("button", {
      key: t,
      onClick: () => setTab(t),
      style: {
        height: 30,
        padding: '0 14px',
        border: 'none',
        borderRadius: 4,
        cursor: 'pointer',
        fontFamily: 'var(--font-sans)',
        fontSize: 13,
        fontWeight: 500,
        background: tab === t ? 'var(--color-surface-elevated)' : 'transparent',
        color: tab === t ? 'var(--color-text)' : 'var(--color-text-muted)',
        boxShadow: tab === t ? 'var(--shadow-sm)' : 'none'
      }
    }, t)))
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 20,
      marginBottom: 16,
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-primary)',
      fontWeight: 600
    }
  }, "14"), " Pending"), /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: 0.4
    }
  }, "\xB7"), /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-critical)',
      fontWeight: 600
    }
  }, "3"), " Overdue"), /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: 0.4
    }
  }, "\xB7"), /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-success)',
      fontWeight: 600
    }
  }, "127"), " Resolved this month")), /*#__PURE__*/React.createElement(Card, {
    padding: 0,
    style: {
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement(DataTable, {
    columns: ['Equipment', 'Characteristic', '%GR&R', 'NDC', 'Submitted', 'Assigned', 'Due', 'Status', ''],
    rows: REVIEW_ROWS.map(r => [/*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)'
      }
    }, r.eq), r.char, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        color: grrColor(r.grr)
      }
    }, r.grr, "%"), /*#__PURE__*/React.createElement(Badge, {
      tone: ndcTone(r.ndc)
    }, r.ndc), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        color: 'var(--color-text-secondary)'
      }
    }, r.submitted), r.assignee, r.overdue ? /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        fontFamily: 'var(--font-mono)',
        color: 'var(--color-critical)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "TriangleAlert",
      size: 13,
      color: "var(--color-critical)"
    }), r.due) : /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        color: 'var(--color-text-secondary)'
      }
    }, r.due), r.overdue ? /*#__PURE__*/React.createElement(Badge, {
      tone: "critical"
    }, "Overdue") : /*#__PURE__*/React.createElement(Badge, {
      tone: "info",
      variant: "outline"
    }, "Pending"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 6,
        justifyContent: 'flex-end'
      }
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      size: "sm",
      onClick: () => setDrawer(r)
    }, "Review"), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      size: "sm",
      icon: /*#__PURE__*/React.createElement(Icon, {
        name: "Ellipsis",
        size: 15
      })
    }))])
  })), drawer && /*#__PURE__*/React.createElement(ReviewDrawer, {
    row: drawer,
    onClose: () => setDrawer(null)
  }));
}
Object.assign(window, {
  ReviewQueue
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/ReviewQueue.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/charts.jsx
try { (() => {
/* Arad UI Kit — charts: SPC I-MR control chart, donut gauge, mini bar chart. */

/* ── SPC Control Chart ──
   props: data [{v, violation}], ucl, cl, lcl, height */
function SPCChart({
  data,
  ucl,
  cl,
  lcl,
  height = 280,
  onPointHover
}) {
  const W = 820,
    H = height,
    padL = 52,
    padR = 16,
    padT = 18,
    padB = 28;
  const plotW = W - padL - padR,
    plotH = H - padT - padB;
  const vals = data.map(d => d.v);
  const lo = Math.min(lcl, ...vals) - (ucl - lcl) * 0.15;
  const hi = Math.max(ucl, ...vals) + (ucl - lcl) * 0.15;
  const rng = hi - lo || 1;
  const x = i => padL + i / (data.length - 1) * plotW;
  const y = v => padT + (1 - (v - lo) / rng) * plotH;
  const linePath = data.map((d, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(d.v).toFixed(1)}`).join(' ');
  const areaPath = `${linePath} L${x(data.length - 1).toFixed(1)},${(padT + plotH).toFixed(1)} L${padL},${(padT + plotH).toFixed(1)} Z`;
  const limitLine = (val, color, dash, labelTxt) => /*#__PURE__*/React.createElement("g", null, /*#__PURE__*/React.createElement("line", {
    x1: padL,
    y1: y(val),
    x2: W - padR,
    y2: y(val),
    stroke: color,
    strokeWidth: "1",
    strokeDasharray: dash,
    opacity: "0.7"
  }), /*#__PURE__*/React.createElement("text", {
    x: W - padR,
    y: y(val) - 4,
    textAnchor: "end",
    fontFamily: "var(--font-mono)",
    fontSize: "10",
    fill: color,
    opacity: "0.9"
  }, labelTxt, " ", val.toFixed(3)));
  return /*#__PURE__*/React.createElement("svg", {
    viewBox: `0 0 ${W} ${H}`,
    width: "100%",
    style: {
      display: 'block',
      overflow: 'visible'
    }
  }, /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("linearGradient", {
    id: "spcFill",
    x1: "0",
    y1: "0",
    x2: "0",
    y2: "1"
  }, /*#__PURE__*/React.createElement("stop", {
    offset: "0%",
    stopColor: "#3B82F6",
    stopOpacity: "0.16"
  }), /*#__PURE__*/React.createElement("stop", {
    offset: "100%",
    stopColor: "#3B82F6",
    stopOpacity: "0"
  }))), [lo, lo + rng * 0.25, lo + rng * 0.5, lo + rng * 0.75, hi].map((v, i) => /*#__PURE__*/React.createElement("text", {
    key: i,
    x: padL - 8,
    y: y(v) + 3,
    textAnchor: "end",
    fontFamily: "var(--font-mono)",
    fontSize: "10",
    fill: "var(--color-text-muted)"
  }, v.toFixed(2))), limitLine(ucl, '#EF4444', '5 4', 'UCL'), limitLine(cl, '#3B82F6', '5 4', 'CL'), limitLine(lcl, '#EF4444', '5 4', 'LCL'), /*#__PURE__*/React.createElement("path", {
    d: areaPath,
    fill: "url(#spcFill)"
  }), /*#__PURE__*/React.createElement("path", {
    d: linePath,
    fill: "none",
    stroke: "#F1F5F9",
    strokeWidth: "1.5"
  }), data.map((d, i) => d.violation ? /*#__PURE__*/React.createElement("g", {
    key: i
  }, /*#__PURE__*/React.createElement("circle", {
    cx: x(i),
    cy: y(d.v),
    r: "6",
    fill: "none",
    stroke: "#EF4444",
    strokeWidth: "1.5"
  }, /*#__PURE__*/React.createElement("animate", {
    attributeName: "r",
    values: "5;12;5",
    dur: "1.8s",
    repeatCount: "indefinite"
  }), /*#__PURE__*/React.createElement("animate", {
    attributeName: "opacity",
    values: "0.7;0;0.7",
    dur: "1.8s",
    repeatCount: "indefinite"
  })), /*#__PURE__*/React.createElement("circle", {
    cx: x(i),
    cy: y(d.v),
    r: "3.5",
    fill: "#EF4444",
    stroke: "#0A0B0F",
    strokeWidth: "1"
  })) : /*#__PURE__*/React.createElement("circle", {
    key: i,
    cx: x(i),
    cy: y(d.v),
    r: "2.5",
    fill: "#94A3B8"
  })));
}

/* ── Donut gauge ── value 0-100, target line */
function DonutGauge({
  value = 97.3,
  target = 95,
  size = 150
}) {
  const r = size / 2 - 12,
    cx = size / 2,
    cy = size / 2,
    circ = 2 * Math.PI * r;
  const animated = useCountUp(value, [value], 900);
  const pass = animated,
    fail = 100 - animated;
  const passLen = pass / 100 * circ,
    failLen = fail / 100 * circ;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      width: size,
      height: size
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    style: {
      transform: 'rotate(-90deg)'
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: cx,
    cy: cy,
    r: r,
    fill: "none",
    stroke: "var(--color-surface-inset)",
    strokeWidth: "10"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: cx,
    cy: cy,
    r: r,
    fill: "none",
    stroke: "#EF4444",
    strokeWidth: "10",
    strokeDasharray: `${failLen} ${circ}`,
    strokeDashoffset: -passLen,
    opacity: "0.85"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: cx,
    cy: cy,
    r: r,
    fill: "none",
    stroke: "#10B981",
    strokeWidth: "10",
    strokeDasharray: `${passLen} ${circ}`,
    strokeLinecap: "round",
    style: {
      filter: 'drop-shadow(0 0 5px rgba(16,185,129,.5))'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 24,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, animated.toFixed(1), "%"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 10,
      letterSpacing: '.06em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginTop: 2
    }
  }, "Accuracy")));
}

/* ── Mini bar chart (daily usage) ── data: number[] */
function MiniBars({
  data,
  color = 'var(--color-secondary)',
  height = 56
}) {
  const max = Math.max(...data) || 1;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      gap: 4,
      height
    }
  }, data.map((v, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    title: `$${v.toFixed(2)}`,
    style: {
      flex: 1,
      height: `${Math.max(6, v / max * 100)}%`,
      background: color,
      opacity: i === data.length - 1 ? 1 : 0.45,
      borderRadius: '2px 2px 0 0',
      transition: 'height var(--transition)'
    }
  })));
}
Object.assign(window, {
  SPCChart,
  DonutGauge,
  MiniBars
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/charts.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/lib.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Arad UI Kit — shared library: icons, primitives, helpers, mock data.
   Cosmetic recreations of the design-system components, scoped to the kit so
   the kit previews standalone. Exported to window for the page scripts. */

const {
  useState,
  useEffect,
  useRef
} = React;

/* ─────────────────────────  ICON (Lucide)  ───────────────────────── */
function Icon({
  name,
  size = 18,
  strokeWidth = 2,
  color = 'currentColor',
  style = {}
}) {
  const node = window.lucide && window.lucide.icons && window.lucide.icons[name];
  if (!node) return React.createElement('span', {
    style: {
      width: size,
      height: size,
      display: 'inline-block'
    }
  });
  const children = node[2] || [];
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    strokeWidth: strokeWidth,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: {
      display: 'block',
      flex: 'none',
      ...style
    }
  }, children.map((c, i) => React.createElement(c[0], {
    key: i,
    ...c[1]
  })));
}

/* ─────────────────────────  HELPERS  ───────────────────────── */
function useCountUp(target, deps = [], duration = 800) {
  const [val, setVal] = useState(target);
  useEffect(() => {
    const num = parseFloat(target);
    if (isNaN(num)) {
      setVal(target);
      return;
    }
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (document.visibilityState !== 'visible' || reduce) {
      setVal(num);
      return;
    }
    let raf, start;
    setVal(0);
    const step = t => {
      if (!start) start = t;
      const p = Math.min((t - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(num * eased);
      if (p < 1) raf = requestAnimationFrame(step);else setVal(num);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, deps); // eslint-disable-line
  return val;
}
function fmt(n, decimals = 0) {
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

/* ─────────────────────────  PRIMITIVES  ───────────────────────── */
function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon = null,
  disabled = false,
  onClick,
  style = {},
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    fontFamily: 'var(--font-sans)',
    fontWeight: 500,
    fontSize: size === 'sm' ? 12 : 13,
    height: size === 'sm' ? 28 : 36,
    padding: size === 'sm' ? '0 10px' : '0 14px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid transparent',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all var(--transition)',
    whiteSpace: 'nowrap',
    userSelect: 'none'
  };
  const variants = {
    primary: {
      background: 'linear-gradient(180deg,#3B82F6,#2563EB)',
      color: '#fff',
      boxShadow: '0 1px 2px rgba(0,0,10,.4)',
      filter: hover && !disabled ? 'brightness(1.1)' : 'none'
    },
    secondary: {
      background: 'var(--color-surface-elevated)',
      border: '1px solid rgba(59,130,246,.4)',
      color: 'var(--color-primary)',
      boxShadow: hover && !disabled ? 'var(--glow-primary)' : 'none'
    },
    destructive: {
      background: '#7F1D1D',
      color: '#FCA5A5'
    },
    ghost: {
      background: hover && !disabled ? 'var(--color-surface-elevated)' : 'transparent',
      color: 'var(--color-text-secondary)'
    }
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    onClick: disabled ? undefined : onClick,
    disabled: disabled,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      ...base,
      ...variants[variant],
      ...style
    }
  }, rest), icon, children);
}
function Badge({
  children,
  tone = 'info',
  variant = 'solid',
  style = {}
}) {
  const tones = {
    pass: ['var(--color-pass-bg)', 'var(--color-pass-text)'],
    conditional: ['var(--color-cond-bg)', 'var(--color-cond-text)'],
    fail: ['var(--color-fail-bg)', 'var(--color-fail-text)'],
    critical: ['var(--color-fail-bg)', 'var(--color-fail-text)'],
    info: ['var(--color-info-bg)', 'var(--color-info-text)'],
    purple: ['var(--color-purple-bg)', 'var(--color-purple-text)'],
    neutral: ['var(--color-surface-elevated)', 'var(--color-text-secondary)']
  };
  const [bg, fg] = tones[tone] || tones.info;
  const skin = variant === 'outline' ? {
    background: 'transparent',
    color: fg,
    border: `1px solid ${fg}`
  } : {
    background: bg,
    color: fg,
    border: '1px solid transparent'
  };
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      lineHeight: 1,
      padding: '4px 8px',
      borderRadius: 'var(--radius-sm)',
      whiteSpace: 'nowrap',
      ...skin,
      ...style
    }
  }, children);
}
function Card({
  children,
  interactive = false,
  accent = null,
  elevated = false,
  padding = 20,
  style = {},
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const accentColors = {
    ai: 'var(--color-secondary)',
    info: 'var(--color-primary)',
    pass: 'var(--color-success)',
    conditional: 'var(--color-warning)',
    fail: 'var(--color-critical)',
    critical: 'var(--color-critical)'
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    onMouseEnter: () => interactive && setHover(true),
    onMouseLeave: () => interactive && setHover(false),
    style: {
      background: elevated ? 'var(--color-surface-elevated)' : 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderLeft: accent ? `3px solid ${accentColors[accent] || accent}` : '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      padding,
      boxShadow: hover ? 'var(--glow-primary)' : 'var(--shadow-sm)',
      transition: 'box-shadow var(--transition), border-color var(--transition)',
      boxSizing: 'border-box',
      ...style
    }
  }, rest), children);
}
function StatusDot({
  tone = 'success',
  pulse = true,
  size = 8,
  label = null,
  style = {}
}) {
  const colors = {
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    info: 'var(--color-primary)',
    purple: 'var(--color-secondary)',
    muted: 'var(--color-text-muted)'
  };
  const c = colors[tone] || colors.success;
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative',
      width: size,
      height: size,
      display: 'inline-block'
    }
  }, pulse && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: '50%',
      background: c,
      animation: 'arad-pulse 1.8s var(--ease-out) infinite'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      inset: 0,
      borderRadius: '50%',
      background: c,
      boxShadow: `0 0 6px ${c}`
    }
  })), label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      color: 'var(--color-text-secondary)'
    }
  }, label));
}
function Sparkline({
  data,
  w = 72,
  h = 28,
  color = 'var(--color-primary)',
  id = 'sp'
}) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data),
    max = Math.max(...data),
    rng = max - min || 1;
  const pts = data.map((v, i) => [i / (data.length - 1) * w, h - (v - min) / rng * h]);
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const gid = 'grad-' + id;
  return /*#__PURE__*/React.createElement("svg", {
    width: w,
    height: h,
    style: {
      overflow: 'visible'
    }
  }, /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("linearGradient", {
    id: gid,
    x1: "0",
    y1: "0",
    x2: "0",
    y2: "1"
  }, /*#__PURE__*/React.createElement("stop", {
    offset: "0%",
    stopColor: color,
    stopOpacity: "0.28"
  }), /*#__PURE__*/React.createElement("stop", {
    offset: "100%",
    stopColor: color,
    stopOpacity: "0"
  }))), /*#__PURE__*/React.createElement("path", {
    d: `${d} L${w},${h} L0,${h} Z`,
    fill: `url(#${gid})`
  }), /*#__PURE__*/React.createElement("path", {
    d: d,
    fill: "none",
    stroke: color,
    strokeWidth: "1.5"
  }));
}
function KPICard({
  label,
  value,
  unit = '',
  subtitle = null,
  subtitleTone = 'muted',
  spark = null,
  animateKey,
  id = 'k'
}) {
  const animated = useCountUp(value, [animateKey]);
  const display = isNaN(parseFloat(value)) ? value : fmt(animated, String(value).includes('.') ? 1 : 0);
  const toneColors = {
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    muted: 'var(--color-text-secondary)',
    info: 'var(--color-primary)'
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      padding: 20,
      boxShadow: 'var(--shadow-sm)',
      minHeight: 112,
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginBottom: 12
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 28,
      fontWeight: 600,
      color: 'var(--color-text)',
      lineHeight: 1,
      letterSpacing: '-.01em'
    }
  }, display, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 16,
      color: 'var(--color-text-secondary)',
      marginLeft: 2
    }
  }, unit)), subtitle && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 500,
      color: toneColors[subtitleTone],
      marginTop: 10,
      paddingRight: spark ? 80 : 0
    }
  }, subtitle), spark && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      right: 16,
      bottom: 16
    }
  }, /*#__PURE__*/React.createElement(Sparkline, {
    data: spark,
    id: id
  })));
}
function MetricPill({
  value,
  label,
  tone = 'default'
}) {
  const toneColors = {
    default: 'var(--color-text)',
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    info: 'var(--color-primary)'
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 96,
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: '12px 14px',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 20,
      fontWeight: 600,
      color: toneColors[tone],
      lineHeight: 1.1
    }
  }, value), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)',
      marginTop: 6
    }
  }, label));
}
function SegmentedBar({
  segments,
  height = 28,
  showLabels = true
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const palette = ['var(--color-primary)', 'var(--color-secondary)', 'var(--color-success)', 'var(--color-warning)'];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      height,
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
      border: '1px solid var(--color-border)'
    }
  }, segments.map((s, i) => {
    const pct = s.value / total * 100;
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        width: `${pct}%`,
        background: s.color || palette[i % palette.length],
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        fontWeight: 600,
        color: 'rgba(255,255,255,.92)'
      }
    }, pct > 10 ? `${s.value}%` : '');
  })), showLabels && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 16,
      marginTop: 10,
      flexWrap: 'wrap'
    }
  }, segments.map((s, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 8,
      borderRadius: 2,
      background: s.color || palette[i % palette.length]
    }
  }), s.label, " ", /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-text)'
    }
  }, s.value, "%")))));
}
function ProgressBar({
  value,
  max = 100,
  tone = 'info',
  label = null,
  valueLabel = null,
  height = 6
}) {
  const pct = Math.max(0, Math.min(100, value / max * 100));
  const colors = {
    info: 'var(--color-primary)',
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
    ai: 'var(--color-secondary)'
  };
  const c = colors[tone];
  return /*#__PURE__*/React.createElement("div", null, (label || valueLabel) && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: 6
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-secondary)'
    }
  }, label), valueLabel && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      color: 'var(--color-text)'
    }
  }, valueLabel)), /*#__PURE__*/React.createElement("div", {
    style: {
      height,
      background: 'var(--color-surface-inset)',
      borderRadius: 999,
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${pct}%`,
      height: '100%',
      borderRadius: 999,
      background: c,
      boxShadow: `0 0 8px ${c}`,
      transition: 'width 600ms var(--ease-out)'
    }
  })));
}
function Input({
  label,
  error,
  hint,
  mono = false,
  value,
  onChange,
  placeholder,
  type = 'text',
  style = {},
  ...rest
}) {
  const [focused, setFocused] = useState(false);
  const borderColor = error ? 'var(--color-critical)' : focused ? 'var(--color-primary)' : 'var(--color-border)';
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-text-muted)'
    }
  }, label), /*#__PURE__*/React.createElement("input", _extends({
    type: type,
    value: value,
    onChange: onChange,
    placeholder: placeholder,
    onFocus: () => setFocused(true),
    onBlur: () => setFocused(false),
    style: {
      height: 40,
      padding: '0 12px',
      background: 'var(--color-surface-inset)',
      border: `1px solid ${borderColor}`,
      borderRadius: 'var(--radius-md)',
      color: 'var(--color-text)',
      fontFamily: mono ? 'var(--font-mono)' : 'var(--font-sans)',
      fontSize: 13,
      outline: 'none',
      boxShadow: focused && !error ? 'var(--ring-focus)' : 'none',
      transition: 'all var(--transition)',
      width: '100%',
      boxSizing: 'border-box'
    }
  }, rest)), error ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-fail-text)'
    }
  }, error) : hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-muted)'
    }
  }, hint) : null);
}
Object.assign(window, {
  Icon,
  useCountUp,
  fmt,
  Button,
  Badge,
  Card,
  StatusDot,
  Sparkline,
  KPICard,
  MetricPill,
  SegmentedBar,
  ProgressBar,
  Input
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/lib.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/shell.jsx
try { (() => {
/* Arad UI Kit — app shell: sidebar, header, footer, layout. */

const NAV = [{
  id: 'dashboard',
  label: 'Dashboard',
  icon: 'House'
}, {
  id: 'grr',
  label: 'GR&R Studies',
  icon: 'ChartColumn'
}, {
  id: 'review',
  label: 'Review Queue',
  icon: 'ClipboardCheck',
  badge: 14
}, {
  id: 'alerts',
  label: 'Alerts',
  icon: 'Bell',
  badge: 3,
  badgeTone: 'critical'
}, {
  id: 'analytics',
  label: 'Analytics',
  icon: 'TrendingUp'
}, {
  id: 'assistant',
  label: 'AI Assistant',
  icon: 'Sparkles'
}, {
  id: 'audit',
  label: 'Audit Log',
  icon: 'Shield'
}];
function Sidebar({
  active,
  onNavigate
}) {
  return /*#__PURE__*/React.createElement("aside", {
    style: {
      width: 220,
      flex: 'none',
      background: 'var(--color-surface)',
      borderRight: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: 64,
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '0 18px',
      borderBottom: '1px solid var(--color-border)'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/arad-mark.svg",
    width: "28",
    height: "28",
    alt: "Arad",
    style: {
      display: 'block'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 15,
      fontWeight: 700,
      color: 'var(--color-text)',
      letterSpacing: '-.01em'
    }
  }, "Arad"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 15,
      fontWeight: 400,
      color: 'var(--color-text-secondary)'
    }
  }, "QI")), /*#__PURE__*/React.createElement("nav", {
    style: {
      flex: 1,
      padding: 12,
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
      overflowY: 'auto'
    }
  }, NAV.map(item => {
    const isActive = active === item.id;
    return /*#__PURE__*/React.createElement("button", {
      key: item.id,
      onClick: () => onNavigate(item.id),
      style: {
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        height: 38,
        padding: '0 12px',
        borderRadius: 'var(--radius-md)',
        border: 'none',
        background: isActive ? 'var(--color-primary-soft)' : 'transparent',
        color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
        cursor: 'pointer',
        fontFamily: 'var(--font-sans)',
        fontSize: 13,
        fontWeight: isActive ? 600 : 500,
        textAlign: 'left',
        width: '100%',
        transition: 'all var(--transition)'
      },
      onMouseEnter: e => {
        if (!isActive) {
          e.currentTarget.style.background = 'var(--color-surface-elevated)';
          e.currentTarget.style.color = 'var(--color-text)';
        }
      },
      onMouseLeave: e => {
        if (!isActive) {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--color-text-secondary)';
        }
      }
    }, isActive && /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        left: -12,
        top: 8,
        bottom: 8,
        width: 3,
        borderRadius: 999,
        background: 'var(--color-primary)'
      }
    }), /*#__PURE__*/React.createElement(Icon, {
      name: item.icon,
      size: 18,
      color: isActive ? 'var(--color-primary)' : 'currentColor'
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1
      }
    }, item.label), item.badge && /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        fontWeight: 600,
        minWidth: 18,
        height: 18,
        padding: '0 5px',
        borderRadius: 999,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: item.badgeTone === 'critical' ? 'var(--color-critical)' : 'var(--color-surface-elevated)',
        color: item.badgeTone === 'critical' ? '#fff' : 'var(--color-text-secondary)'
      }
    }, item.badge));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 12,
      borderTop: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => onNavigate('settings'),
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      height: 38,
      padding: '0 12px',
      borderRadius: 'var(--radius-md)',
      border: 'none',
      background: active === 'settings' ? 'var(--color-primary-soft)' : 'transparent',
      color: active === 'settings' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
      cursor: 'pointer',
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      fontWeight: 500,
      width: '100%'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Settings",
    size: 18
  }), /*#__PURE__*/React.createElement("span", null, "Settings")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '8px',
      borderRadius: 'var(--radius-md)',
      background: 'var(--color-surface-inset)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 32,
      height: 32,
      borderRadius: 999,
      background: 'linear-gradient(135deg,#6366F1,#3B82F6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 600,
      color: '#fff',
      flex: 'none'
    }
  }, "DK"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 600,
      color: 'var(--color-text)',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    }
  }, "Vertex Aerospace"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 10,
      color: 'var(--color-text-muted)'
    }
  }, "D. Karam")), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 9,
      fontWeight: 600,
      letterSpacing: '.06em',
      textTransform: 'uppercase',
      color: 'var(--color-secondary)',
      border: '1px solid var(--color-secondary)',
      borderRadius: 4,
      padding: '2px 5px'
    }
  }, "Ent"))));
}
function Header({
  breadcrumb,
  range,
  onRange
}) {
  const ranges = ['24h', '7d', '30d', 'Custom'];
  return /*#__PURE__*/React.createElement("header", {
    style: {
      height: 64,
      flex: 'none',
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      padding: '0 24px',
      borderBottom: '1px solid var(--color-border)',
      background: 'rgba(10,11,15,0.7)',
      backdropFilter: 'blur(8px)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      fontFamily: 'var(--font-sans)',
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-text-muted)'
    }
  }, "Arad"), /*#__PURE__*/React.createElement(Icon, {
    name: "ChevronRight",
    size: 14,
    color: "var(--color-text-muted)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-text)',
      fontWeight: 600
    }
  }, breadcrumb)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      height: 36,
      padding: '0 12px',
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      width: 240
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Search",
    size: 15,
    color: "var(--color-text-muted)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text-muted)'
    }
  }, "Search\u2026"), /*#__PURE__*/React.createElement("kbd", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 10,
      color: 'var(--color-text-muted)',
      border: '1px solid var(--color-border-strong)',
      borderRadius: 4,
      padding: '1px 5px'
    }
  }, "\u2318K")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      background: 'var(--color-surface-inset)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: 2
    }
  }, ranges.map(r => /*#__PURE__*/React.createElement("button", {
    key: r,
    onClick: () => onRange(r),
    style: {
      height: 28,
      padding: '0 10px',
      border: 'none',
      borderRadius: 4,
      cursor: 'pointer',
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 500,
      background: range === r ? 'var(--color-surface-elevated)' : 'transparent',
      color: range === r ? 'var(--color-text)' : 'var(--color-text-muted)',
      boxShadow: range === r ? 'var(--shadow-sm)' : 'none'
    }
  }, r))), /*#__PURE__*/React.createElement(StatusDot, {
    tone: "success",
    label: "Live"
  }), /*#__PURE__*/React.createElement("button", {
    style: {
      position: 'relative',
      width: 36,
      height: 36,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'transparent',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      cursor: 'pointer',
      color: 'var(--color-text-secondary)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Bell",
    size: 17
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: -4,
      right: -4,
      minWidth: 16,
      height: 16,
      padding: '0 4px',
      borderRadius: 999,
      background: 'var(--color-critical)',
      color: '#fff',
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      fontWeight: 700,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: '2px solid var(--color-bg)'
    }
  }, "3")), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 32,
      height: 32,
      borderRadius: 999,
      background: 'linear-gradient(135deg,#6366F1,#3B82F6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      fontWeight: 600,
      color: '#fff',
      cursor: 'pointer'
    }
  }, "DK"));
}
function Footer() {
  return /*#__PURE__*/React.createElement("footer", {
    style: {
      flex: 'none',
      height: 36,
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '0 24px',
      borderTop: '1px solid var(--color-border)',
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      color: 'var(--color-text-muted)'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "Lock",
    size: 12,
    color: "var(--color-text-muted)"
  }), /*#__PURE__*/React.createElement("span", null, "All data encrypted in transit"), /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: 0.5
    }
  }, "\xB7"), /*#__PURE__*/React.createElement("span", null, "SOC 2 Type II"), /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: 0.5
    }
  }, "\xB7"), /*#__PURE__*/React.createElement("span", null, "Full audit trail"));
}
function PageHeader({
  title,
  subtitle,
  actions
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      marginBottom: 20
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontFamily: 'var(--font-sans)',
      fontSize: 20,
      fontWeight: 600,
      color: 'var(--color-text)'
    }
  }, title), subtitle && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 4,
      fontFamily: 'var(--font-sans)',
      fontSize: 13,
      color: 'var(--color-text-secondary)'
    }
  }, subtitle)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), actions);
}
Object.assign(window, {
  Sidebar,
  Header,
  Footer,
  PageHeader,
  NAV
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/shell.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.KPICard = __ds_scope.KPICard;

__ds_ns.MetricPill = __ds_scope.MetricPill;

__ds_ns.SegmentedBar = __ds_scope.SegmentedBar;

__ds_ns.ProgressBar = __ds_scope.ProgressBar;

__ds_ns.StatusDot = __ds_scope.StatusDot;

})();
