import { Document, Page, View, Text, StyleSheet } from "@react-pdf/renderer";
import type { GRRAnalysisResponse } from "@/api/apiClient";

export type GRRPdfReportProps = {
  analysis: GRRAnalysisResponse;
  processName: string;
  operators: number;
  parts: number;
  trials: number;
  partTolerance?: number;
};

type VerdictMeta = { label: string; color: string; bg: string; border: string };

function verdictMeta(pct: number): VerdictMeta {
  if (pct < 10) return { label: "ACCEPTABLE", color: "#059669", bg: "#ecfdf5", border: "#a7f3d0" };
  if (pct <= 30) return { label: "CONDITIONALLY ACCEPTABLE", color: "#b45309", bg: "#fffbeb", border: "#fde68a" };
  return { label: "UNACCEPTABLE", color: "#b91c1c", bg: "#fef2f2", border: "#fecaca" };
}

const c = {
  white: "#ffffff",
  ink: "#0f172a",
  ink2: "#1e293b",
  muted: "#64748b",
  subtle: "#94a3b8",
  border: "#e2e8f0",
  surface: "#f8fafc",
  accent: "#4f6bef",
} as const;

const s = StyleSheet.create({
  page: {
    backgroundColor: c.white,
    paddingHorizontal: 52,
    paddingVertical: 44,
    fontFamily: "Helvetica",
    fontSize: 10,
    color: c.ink,
  },
  accentBar: { height: 4, backgroundColor: c.accent, borderRadius: 2, marginBottom: 22 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 },
  brandName: { fontSize: 22, fontFamily: "Helvetica-Bold", color: c.ink, letterSpacing: 4 },
  brandSub: { fontSize: 7, color: c.muted, marginTop: 3, letterSpacing: 2 },
  headerDate: { fontSize: 9, color: c.muted, textAlign: "right" },
  headerConf: { fontSize: 8, color: c.muted, marginTop: 2, letterSpacing: 1, textAlign: "right" },
  rule: { height: 1, backgroundColor: c.border, marginBottom: 22 },

  reportTitle: { fontSize: 20, fontFamily: "Helvetica-Bold", color: c.ink, marginBottom: 4 },
  processNameText: { fontSize: 12, color: c.muted, marginBottom: 14 },

  metaRow: { flexDirection: "row", marginBottom: 18 },
  metaChip: {
    flexDirection: "row",
    backgroundColor: c.surface,
    borderWidth: 1, borderColor: c.border, borderStyle: "solid",
    borderRadius: 6,
    paddingHorizontal: 10, paddingVertical: 5,
    marginRight: 8,
  },
  metaLabel: { fontSize: 7.5, color: c.muted, marginRight: 4 },
  metaValue: { fontSize: 8, fontFamily: "Helvetica-Bold", color: c.ink },

  verdictBanner: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    borderWidth: 1, borderStyle: "solid", borderRadius: 10,
    paddingHorizontal: 20, paddingVertical: 16, marginBottom: 8,
  },
  verdictLabel: { fontSize: 13, fontFamily: "Helvetica-Bold", letterSpacing: 0.8, marginBottom: 3 },
  verdictSub: { fontSize: 8 },
  verdictPct: { fontSize: 34, fontFamily: "Helvetica-Bold" },

  progressTrack: {
    height: 6, backgroundColor: c.border, borderRadius: 3, marginBottom: 22,
  },
  progressFill: { height: 6, borderRadius: 3 },

  sectionLabel: {
    fontSize: 8, fontFamily: "Helvetica-Bold", color: c.muted, letterSpacing: 2, marginBottom: 10,
  },

  metricsGrid: { flexDirection: "row", marginBottom: 18 },
  metricCard: {
    flex: 1,
    backgroundColor: c.surface,
    borderWidth: 1, borderColor: c.border, borderStyle: "solid",
    borderRadius: 8, padding: 12, marginRight: 8,
  },
  metricCardLabel: { fontSize: 7.5, color: c.muted, letterSpacing: 1, marginBottom: 5 },
  metricCardValue: { fontSize: 17, fontFamily: "Helvetica-Bold", color: c.ink, marginBottom: 3 },
  metricCardSub: { fontSize: 7.5, color: c.subtle },

  guideBox: {
    backgroundColor: c.surface,
    borderWidth: 1, borderColor: c.border, borderStyle: "solid",
    borderRadius: 8, padding: 14, marginBottom: 18,
  },
  guideRow: { flexDirection: "row", marginBottom: 5 },
  guideRange: { width: 52, fontSize: 8.5, fontFamily: "Helvetica-Bold" },
  guideText: { flex: 1, fontSize: 8.5, color: c.ink2 },

  aiBox: {
    backgroundColor: c.surface,
    borderWidth: 1, borderColor: c.border, borderStyle: "solid",
    borderRadius: 8, padding: 16, flex: 1,
  },
  aiText: { fontSize: 9.5, color: c.ink2, lineHeight: 1.7 },

  footer: {
    flexDirection: "row", justifyContent: "space-between",
    borderTopWidth: 1, borderTopColor: c.border, borderTopStyle: "solid",
    paddingTop: 12, marginTop: 18,
  },
  footerText: { fontSize: 7.5, color: c.subtle },
});

export function GRRPdfReport({
  analysis,
  processName,
  operators,
  parts,
  trials,
  partTolerance,
}: GRRPdfReportProps) {
  const v = verdictMeta(analysis.grr_percent);
  const pct = Math.min(Math.max(analysis.grr_percent, 0), 100);
  const generatedAt = new Date(analysis.timestamp).toLocaleString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const metaChips = [
    { label: "OPERATORS", value: String(operators) },
    { label: "PARTS", value: String(parts) },
    { label: "TRIALS", value: String(trials) },
    ...(partTolerance != null ? [{ label: "TOLERANCE", value: partTolerance.toFixed(4) }] : []),
  ];

  const metrics = [
    { label: "GR&R TOTAL", value: `${analysis.grr_percent.toFixed(2)}%`, sub: "Total system variation" },
    { label: "REPEATABILITY", value: analysis.repeatability.toFixed(4), sub: "Equipment variation (EV)" },
    { label: "REPRODUCIBILITY", value: analysis.reproducibility.toFixed(4), sub: "Appraiser variation (AV)" },
    { label: "NDC", value: String(analysis.number_of_distinct_categories), sub: "Distinct categories (≥5)" },
  ];

  return (
    <Document
      title={`GR&R Report – ${processName}`}
      author="Arad Quality Intelligence"
      subject="Gauge Repeatability & Reproducibility Analysis"
      creator="Arad Quality Intelligence Platform"
    >
      <Page size="A4" style={s.page}>
        <View style={s.accentBar} />

        <View style={s.headerRow}>
          <View>
            <Text style={s.brandName}>ARAD</Text>
            <Text style={s.brandSub}>QUALITY INTELLIGENCE PLATFORM</Text>
          </View>
          <View>
            <Text style={s.headerDate}>{generatedAt}</Text>
            <Text style={s.headerConf}>CONFIDENTIAL — Internal Use Only</Text>
          </View>
        </View>
        <View style={s.rule} />

        <Text style={s.reportTitle}>GR&R Measurement System Analysis</Text>
        <Text style={s.processNameText}>Process: {processName || "Unnamed Process"}</Text>

        <View style={s.metaRow}>
          {metaChips.map((chip) => (
            <View key={chip.label} style={s.metaChip}>
              <Text style={s.metaLabel}>{chip.label}: </Text>
              <Text style={s.metaValue}>{chip.value}</Text>
            </View>
          ))}
        </View>

        <View style={[s.verdictBanner, { backgroundColor: v.bg, borderColor: v.border }]}>
          <View>
            <Text style={[s.verdictLabel, { color: v.color }]}>{v.label}</Text>
            <Text style={[s.verdictSub, { color: v.color }]}>AIAG Measurement System Assessment</Text>
          </View>
          <Text style={[s.verdictPct, { color: v.color }]}>{analysis.grr_percent.toFixed(1)}%</Text>
        </View>

        <View style={s.progressTrack}>
          <View style={[s.progressFill, { width: `${pct}%`, backgroundColor: v.color }]} />
        </View>

        <Text style={s.sectionLabel}>MEASUREMENT SYSTEM METRICS</Text>
        <View style={s.metricsGrid}>
          {metrics.map((m, i) => (
            <View key={m.label} style={i === metrics.length - 1 ? [s.metricCard, { marginRight: 0 }] : s.metricCard}>
              <Text style={s.metricCardLabel}>{m.label}</Text>
              <Text style={s.metricCardValue}>{m.value}</Text>
              <Text style={s.metricCardSub}>{m.sub}</Text>
            </View>
          ))}
        </View>

        <View style={s.guideBox}>
          <Text style={[s.sectionLabel, { marginBottom: 8 }]}>AIAG ACCEPTANCE CRITERIA</Text>
          {[
            { range: "< 10%", text: "Acceptable — measurement system is fully capable", color: "#059669" },
            { range: "10–30%", text: "Conditionally acceptable — evaluate based on application criticality", color: "#b45309" },
            { range: "> 30%", text: "Unacceptable — measurement system must be improved before use", color: "#b91c1c" },
          ].map((row) => (
            <View key={row.range} style={s.guideRow}>
              <Text style={[s.guideRange, { color: row.color }]}>{row.range}</Text>
              <Text style={s.guideText}>{row.text}</Text>
            </View>
          ))}
        </View>

        <Text style={[s.sectionLabel, { marginBottom: 8 }]}>AI ANALYSIS & RECOMMENDATIONS</Text>
        <View style={s.aiBox}>
          <Text style={s.aiText}>{analysis.ai_analysis}</Text>
        </View>

        <View style={s.footer}>
          <Text style={s.footerText}>Arad Group — Quality Intelligence Platform</Text>
          <Text style={s.footerText}>{generatedAt}</Text>
          <Text style={s.footerText}>CONFIDENTIAL</Text>
        </View>
      </Page>
    </Document>
  );
}
