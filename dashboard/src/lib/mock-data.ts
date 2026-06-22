// ═══════════════════════════════════════════════════════════════════════════
// Realistic manufacturing mock data for the Arad Quality Intelligence Platform
// ═══════════════════════════════════════════════════════════════════════════

const NOW = new Date("2026-05-26T12:00:00Z").getTime();

export interface GRRStudy {
  id: string;
  equipment_id: string;
  characteristic_name: string;
  part_number: string;
  method: "xbar_r" | "anova";
  grr_pct: number;
  ev: number;
  av: number;
  pv: number;
  ndc: number;
  verdict: "acceptable" | "conditional" | "unacceptable";
  created_at: Date;
  operators: number;
  parts: number;
  trials: number;
  ai_narrative?: string;
}

export interface SPCDataPoint {
  index: number;
  value: number;
  timestamp: Date;
  violation?: string;
}

export interface SPCChart {
  id: string;
  machine_id: string;
  part_number: string;
  characteristic: string;
  chart_type: "xbar_r" | "i_mr" | "p_chart";
  ucl: number;
  cl: number;
  lcl: number;
  data: SPCDataPoint[];
  active_violations: { rule: string; points: number[]; severity: string }[];
  status: "stable" | "warning" | "critical";
}

export interface QualityAlert {
  id: string;
  rule: string;
  rule_label: string;
  severity: "critical" | "warning" | "info";
  machine_id: string;
  part_number: string;
  characteristic: string;
  message: string;
  ai_analysis: string;
  recommended_action: string;
  created_at: Date;
  acknowledged: boolean;
  assignee?: string;
  status: "open" | "investigating" | "resolved";
}

export interface AIInsight {
  id: string;
  type: "anomaly" | "prediction" | "recommendation" | "summary";
  severity: "critical" | "warning" | "info";
  title: string;
  description: string;
  confidence: number;
  source: string;
  created_at: Date;
  actions: { label: string; type: "primary" | "secondary" }[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  widgets?: ChatWidget[];
}

export interface ChatWidget {
  type: "chart" | "table" | "metric" | "alert";
  title: string;
  data: Record<string, unknown>;
}

// ── GRR Studies ──────────────────────────────────────────────────────────────

export const grrStudies: GRRStudy[] = [
  {
    id: "grr-001",
    equipment_id: "CMM-001",
    characteristic_name: "Bore Diameter",
    part_number: "P-2847",
    method: "xbar_r",
    grr_pct: 8.4,
    ev: 0.00312,
    av: 0.00187,
    pv: 0.04210,
    ndc: 12,
    verdict: "acceptable",
    created_at: new Date(NOW - 2 * 3600000),
    operators: 3,
    parts: 10,
    trials: 3,
    ai_narrative: "CMM-001 demonstrates excellent measurement capability for bore diameter on P-2847. The 8.4% GR&R is well within AIAG acceptability limits. Repeatability (EV) dominates at 62% of total GR&R, suggesting minor probe settling variation. NDC of 12 provides strong process discrimination. No action required — approve for production use.",
  },
  {
    id: "grr-002",
    equipment_id: "CMM-002",
    characteristic_name: "Thread Pitch",
    part_number: "P-3921",
    method: "anova",
    grr_pct: 24.7,
    ev: 0.00891,
    av: 0.01234,
    pv: 0.03567,
    ndc: 5,
    verdict: "conditional",
    created_at: new Date(NOW - 8 * 3600000),
    operators: 3,
    parts: 10,
    trials: 3,
    ai_narrative: "CMM-002 shows conditional measurement capability for thread pitch. At 24.7% GR&R, reproducibility (AV) exceeds repeatability — operator technique variation is the dominant error source. NDC of 5 is borderline. Recommend: (1) Standardize fixturing procedure across all operators, (2) Retrain Operator C on probe approach angle, (3) Re-study within 30 days.",
  },
  {
    id: "grr-003",
    equipment_id: "VMM-003",
    characteristic_name: "Surface Roughness Ra",
    part_number: "P-1456",
    method: "xbar_r",
    grr_pct: 42.1,
    ev: 0.02145,
    av: 0.00890,
    pv: 0.03210,
    ndc: 3,
    verdict: "unacceptable",
    created_at: new Date(NOW - 24 * 3600000),
    operators: 3,
    parts: 10,
    trials: 3,
    ai_narrative: "VMM-003 FAILS GR&R for surface roughness measurement. At 42.1%, the measurement system consumes nearly half the tolerance. Repeatability is the dominant error — stylus tip wear or calibration drift is the most probable root cause. NDC of 3 means the gauge cannot distinguish process variation from measurement error. IMMEDIATE ACTION: Remove from production inspection, replace stylus assembly, recalibrate, and re-study.",
  },
  {
    id: "grr-004",
    equipment_id: "CMM-001",
    characteristic_name: "Pin Height",
    part_number: "P-5082",
    method: "anova",
    grr_pct: 6.2,
    ev: 0.00201,
    av: 0.00098,
    pv: 0.05123,
    ndc: 16,
    verdict: "acceptable",
    created_at: new Date(NOW - 48 * 3600000),
    operators: 3,
    parts: 10,
    trials: 3,
  },
  {
    id: "grr-005",
    equipment_id: "OGP-004",
    characteristic_name: "Slot Width",
    part_number: "P-7734",
    method: "xbar_r",
    grr_pct: 18.9,
    ev: 0.00567,
    av: 0.00734,
    pv: 0.04012,
    ndc: 7,
    verdict: "conditional",
    created_at: new Date(NOW - 72 * 3600000),
    operators: 3,
    parts: 10,
    trials: 3,
  },
];

// ── SPC Data ─────────────────────────────────────────────────────────────────

function generateSPCData(cl: number, sigma: number, count: number, anomalies?: { index: number; offset: number }[]): SPCDataPoint[] {
  const data: SPCDataPoint[] = [];
  for (let i = 0; i < count; i++) {
    let value = cl + (Math.random() - 0.5) * sigma * 2;
    const anomaly = anomalies?.find(a => a.index === i);
    if (anomaly) value = cl + anomaly.offset * sigma;
    data.push({
      index: i,
      value: parseFloat(value.toFixed(4)),
      timestamp: new Date(NOW - (count - i) * 900000),
      violation: anomaly ? "rule_1" : undefined,
    });
  }
  return data;
}

export const spcCharts: SPCChart[] = [
  {
    id: "spc-001",
    machine_id: "CMM-001",
    part_number: "P-2847",
    characteristic: "Bore Diameter",
    chart_type: "xbar_r",
    ucl: 25.0312,
    cl: 25.0200,
    lcl: 25.0088,
    data: generateSPCData(25.02, 0.004, 40, [{ index: 32, offset: 3.5 }, { index: 37, offset: -2.8 }]),
    active_violations: [
      { rule: "Rule 1", points: [32, 37], severity: "critical" },
    ],
    status: "critical",
  },
  {
    id: "spc-002",
    machine_id: "CNC-L4-001",
    part_number: "P-3921",
    characteristic: "Thread Pitch",
    chart_type: "xbar_r",
    ucl: 1.2515,
    cl: 1.2500,
    lcl: 1.2485,
    data: generateSPCData(1.25, 0.001, 40),
    active_violations: [],
    status: "stable",
  },
  {
    id: "spc-003",
    machine_id: "VMM-003",
    part_number: "P-1456",
    characteristic: "Surface Roughness",
    chart_type: "i_mr",
    ucl: 0.842,
    cl: 0.800,
    lcl: 0.758,
    data: generateSPCData(0.80, 0.015, 40, [
      { index: 28, offset: 2.1 },
      { index: 29, offset: 2.3 },
      { index: 30, offset: 2.5 },
      { index: 31, offset: 2.0 },
    ]),
    active_violations: [
      { rule: "Rule 2", points: [28, 29, 30, 31], severity: "warning" },
    ],
    status: "warning",
  },
  {
    id: "spc-004",
    machine_id: "PRESS-007",
    part_number: "P-9182",
    characteristic: "Forming Force",
    chart_type: "xbar_r",
    ucl: 245.8,
    cl: 240.0,
    lcl: 234.2,
    data: generateSPCData(240, 2.0, 40),
    active_violations: [],
    status: "stable",
  },
];

// ── Alerts ───────────────────────────────────────────────────────────────────

export const qualityAlerts: QualityAlert[] = [
  {
    id: "alert-001",
    rule: "rule_1",
    rule_label: "Nelson Rule 1",
    severity: "critical",
    machine_id: "CMM-001",
    part_number: "P-2847",
    characteristic: "Bore Diameter",
    message: "Point beyond 3σ control limit detected on XBar-R chart. Value 25.0340 exceeds UCL of 25.0312.",
    ai_analysis: "This extreme outlier at subgroup 32 indicates a sudden special-cause event. The 3.5σ deviation is consistent with a fixture shift, probe collision, or part misalignment during measurement. This is NOT gradual drift — it's an acute event.",
    recommended_action: "Immediately verify CMM-001 probe calibration. Inspect fixture for P-2847 bore diameter setup. Re-measure the flagged subgroup. If repeatable, escalate to metrology team.",
    created_at: new Date(NOW - 45 * 60000),
    acknowledged: false,
    status: "open",
  },
  {
    id: "alert-002",
    rule: "rule_2",
    rule_label: "Nelson Rule 2",
    severity: "warning",
    machine_id: "VMM-003",
    part_number: "P-1456",
    characteristic: "Surface Roughness",
    message: "9 consecutive points above center line detected. Sustained shift pattern on I-MR chart.",
    ai_analysis: "Four consecutive points trending above CL with increasing magnitude suggests progressive tool wear on the finishing operation. The drift pattern matches a worn cutting insert approaching end-of-life. Historical data shows similar patterns preceded tool breakage by 2-3 shifts.",
    recommended_action: "Schedule cutting insert replacement during next planned downtime. Monitor surface roughness Cpk over next shift. If Ra exceeds 0.84 μm, halt production for immediate tool change.",
    created_at: new Date(NOW - 2 * 3600000),
    acknowledged: true,
    assignee: "Sarah Chen",
    status: "investigating",
  },
  {
    id: "alert-003",
    rule: "rule_1",
    rule_label: "Nelson Rule 1",
    severity: "critical",
    machine_id: "CMM-001",
    part_number: "P-2847",
    characteristic: "Bore Diameter",
    message: "Second outlier detected — value 24.9889 below LCL of 25.0088 at subgroup 37.",
    ai_analysis: "Two Rule 1 violations within 5 subgroups on the same characteristic is a strong signal of intermittent fixture instability. The violations are on opposite sides of CL, ruling out systematic bias. Most probable cause: loose workholding or inconsistent datum seating.",
    recommended_action: "Stop production inspection with CMM-001 for P-2847 bore diameter. Perform full fixture verification. Check clamping force consistency. Conduct 3-run repeatability check before resuming.",
    created_at: new Date(NOW - 25 * 60000),
    acknowledged: false,
    status: "open",
  },
  {
    id: "alert-004",
    rule: "grr_failure",
    rule_label: "GR&R Failure",
    severity: "critical",
    machine_id: "VMM-003",
    part_number: "P-1456",
    characteristic: "Surface Roughness Ra",
    message: "GR&R study failed at 42.1%. Equipment VMM-003 is not acceptable for production use.",
    ai_analysis: "The 42.1% GR&R is dominated by repeatability error (EV = 71% of total GR&R), pointing to equipment-level issues rather than operator technique. Stylus tip degradation and probe mounting looseness are the most probable root causes given this equipment's age and usage pattern.",
    recommended_action: "Remove VMM-003 from production inspection immediately. Replace stylus assembly. Recalibrate probing system. Re-run GR&R study with fresh stylus before reinstatement.",
    created_at: new Date(NOW - 24 * 3600000),
    acknowledged: true,
    assignee: "Mike Torres",
    status: "investigating",
  },
  {
    id: "alert-005",
    rule: "rule_3",
    rule_label: "Nelson Rule 3",
    severity: "warning",
    machine_id: "PRESS-007",
    part_number: "P-9182",
    characteristic: "Forming Force",
    message: "6 points in continuous increasing trend detected on forming force chart.",
    ai_analysis: "Monotonic upward trend in forming force is consistent with die wear increasing friction, or hydraulic system pressure regulation degrading. The trend has not yet reached control limits but will breach UCL within an estimated 8-12 subgroups at current rate.",
    recommended_action: "Schedule die inspection during next planned changeover. Check hydraulic pressure regulator calibration. Monitor forming force closely over next 2 shifts.",
    created_at: new Date(NOW - 6 * 3600000),
    acknowledged: false,
    status: "open",
  },
];

// ── AI Insights ──────────────────────────────────────────────────────────────

export const aiInsights: AIInsight[] = [
  {
    id: "insight-001",
    type: "anomaly",
    severity: "critical",
    title: "3 critical process anomalies detected in last 4 hours",
    description: "CMM-001 bore diameter inspection showing intermittent fixture instability. Two Rule 1 violations within 5 subgroups — both opposite sides of CL. Immediate fixture verification required.",
    confidence: 94,
    source: "SPC Monitor • CMM-001 • P-2847",
    created_at: new Date(NOW - 25 * 60000),
    actions: [
      { label: "Investigate", type: "primary" },
      { label: "Escalate to Metrology", type: "secondary" },
    ],
  },
  {
    id: "insight-002",
    type: "prediction",
    severity: "warning",
    title: "VMM-003 surface roughness trending toward UCL breach",
    description: "Progressive drift detected over last 12 subgroups. At current rate, UCL breach predicted within 2-3 shifts. Pattern consistent with cutting insert wear approaching end-of-life.",
    confidence: 87,
    source: "Predictive Analytics • VMM-003 • P-1456",
    created_at: new Date(NOW - 2 * 3600000),
    actions: [
      { label: "Schedule Tool Change", type: "primary" },
      { label: "Monitor", type: "secondary" },
    ],
  },
  {
    id: "insight-003",
    type: "recommendation",
    severity: "info",
    title: "GR&R re-study recommended for CMM-002 thread pitch",
    description: "Conditional result (24.7%) with operator-dominant variation. Standardized fixturing procedure and Operator C retraining should reduce AV by an estimated 35-40%.",
    confidence: 78,
    source: "GR&R Analysis • CMM-002 • P-3921",
    created_at: new Date(NOW - 8 * 3600000),
    actions: [
      { label: "Schedule Re-study", type: "primary" },
      { label: "View Full Report", type: "secondary" },
    ],
  },
];

// ── System Metrics ───────────────────────────────────────────────────────────

export const systemMetrics = {
  total_studies: 47,
  studies_this_week: 5,
  pass_rate: 68.1,
  active_machines: 12,
  monitored_characteristics: 34,
  open_violations: 8,
  alert_accuracy: 96.2,
  mttr_hours: 4.2,
  active_spc_charts: 4,
  avg_grr: 15.8,
};

// ── Chat Example ─────────────────────────────────────────────────────────────

export const exampleChat: ChatMessage[] = [
  {
    id: "msg-001",
    role: "user",
    content: "Which equipment had the worst GR&R this week?",
    timestamp: new Date(NOW - 10 * 60000),
  },
  {
    id: "msg-002",
    role: "assistant",
    content: "VMM-003 had the worst GR&R result this week with **42.1% GR&R** on Surface Roughness Ra measurement for part P-1456.\n\n**Key Findings:**\n- **Verdict:** Unacceptable (>30%)\n- **Dominant Error:** Repeatability (EV) — 71% of total GR&R\n- **NDC:** 3 (below minimum threshold of 5)\n- **Root Cause:** Stylus tip wear and probe mounting looseness\n\n**Recommended Actions:**\n1. Remove VMM-003 from production inspection immediately\n2. Replace stylus assembly and recalibrate\n3. Re-run GR&R study before reinstatement\n\nThe next worst was CMM-002 at 24.7% (conditional) on thread pitch — that one is operator-technique driven, not equipment.",
    timestamp: new Date(NOW - 9 * 60000),
    widgets: [
      {
        type: "metric",
        title: "VMM-003 GR&R Result",
        data: { grr_pct: 42.1, verdict: "unacceptable", ev_pct: 71, av_pct: 29, ndc: 3 },
      },
    ],
  },
];
