"use client";

/* Review Queue — prototype-exact table + sliding decision drawer, wired to /api/v1/reviews. */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Sparkles, TriangleAlert, X, Check } from "lucide-react";
import { decideReview, getReviews, showToast, type ReviewQueueItem } from "@/api/apiClient";
import { Card, MetricPill } from "@/components/ui/kit";
import { toast } from "@/components/ui/fx";
import { parseApiDate } from "@/lib/utils";

function grrColor(g: number | null | undefined) {
  if (g == null) return "var(--text-secondary)";
  return g > 30 ? "var(--critical)" : g > 10 ? "var(--warning)" : "var(--success)";
}

function ndcBadge(n: number | null | undefined) {
  if (n == null) return "badge badge-neutral";
  return n >= 5 ? "badge badge-success" : n >= 2 ? "badge badge-warning" : "badge badge-critical";
}

function shortDate(value?: string | null) {
  if (!value) return "—";
  const d = parseApiDate(value);
  if (Number.isNaN(d.getTime())) return value;
  return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function isOverdue(due?: string | null) {
  if (!due) return false;
  const d = new Date(due);
  return !Number.isNaN(d.getTime()) && d.getTime() < Date.now();
}

const tdS: React.CSSProperties = {
  padding: "12px 20px",
  fontFamily: "var(--font-sans)",
  fontSize: 13,
  color: "var(--text-primary)",
  borderBottom: "1px solid var(--border-default)",
  whiteSpace: "nowrap",
};

function ReviewDrawer({
  row,
  onClose,
  onSubmit,
  submitting,
}: {
  row: ReviewQueueItem;
  onClose: () => void;
  onSubmit: (row: ReviewQueueItem, decision: "approved" | "rejected", notes: string) => void;
  submitting: boolean;
}) {
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);
  const [notes, setNotes] = useState("");
  const [shown, setShown] = useState(false);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setShown(true), 20);
    return () => clearTimeout(t);
  }, []);

  const close = () => {
    setClosing(true);
    setShown(false);
    setTimeout(onClose, 260);
  };

  const open = shown && !closing;
  const grr = row.grr_pct ?? null;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 60 }}>
      <div
        onClick={close}
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(0,0,8,.5)",
          backdropFilter: "blur(2px)",
          opacity: open ? 1 : 0,
          transition: "opacity .26s var(--ease-out)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          bottom: 0,
          width: 480,
          maxWidth: "94vw",
          background: "var(--bg-surface)",
          borderLeft: "1px solid var(--border-default)",
          boxShadow: "-12px 0 48px rgba(0,0,10,.6)",
          display: "flex",
          flexDirection: "column",
          transform: open ? "translateX(0)" : "translateX(480px)",
          transition: "transform .3s cubic-bezier(.32,.72,0,1)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", padding: "18px 22px", borderBottom: "1px solid var(--border-default)" }}>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>{row.equipment_id}</div>
            <div style={{ fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--text-secondary)" }}>{row.characteristic_name}</div>
          </div>
          <div style={{ flex: 1 }} />
          <button onClick={close} className="btn-icon" aria-label="Close drawer">
            <X size={16} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: 22, display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="arad-reveal-sm" style={{ "--d": "60ms", display: "flex", gap: 10 } as React.CSSProperties}>
            <MetricPill
              value={grr != null ? `${grr.toFixed(1)}%` : "—"}
              label="%GR&R"
              tone={grr == null ? "default" : grr > 30 ? "critical" : grr > 10 ? "warning" : "success"}
            />
            <MetricPill
              value={row.ndc ?? "—"}
              label="NDC"
              tone={row.ndc == null ? "default" : row.ndc >= 5 ? "success" : row.ndc >= 2 ? "warning" : "critical"}
            />
            <MetricPill value={shortDate(row.created_at)} label="Submitted" />
          </div>

          <div className="arad-reveal-sm" style={{ "--d": "160ms" } as React.CSSProperties}>
            <div
              style={{
                borderLeft: "3px solid var(--accent-ai)",
                background: "var(--bg-primary)",
                borderRadius: "0 var(--radius-md) var(--radius-md) 0",
                padding: 16,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <Sparkles size={15} style={{ color: "var(--accent-ai)" }} />
                <span style={{ fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>AI Analysis</span>
                <span className={grr != null && grr > 30 ? "badge badge-critical" : "badge badge-warning"} style={{ marginLeft: "auto" }}>
                  Risk: {grr != null && grr > 30 ? "High" : "Medium"}
                </span>
              </div>
              <p style={{ margin: 0, fontFamily: "var(--font-sans)", fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)" }}>
                %GR&R of <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{grr != null ? `${grr.toFixed(1)}%` : "n/a"}</span>{" "}
                with NDC <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{row.ndc ?? "n/a"}</span>.{" "}
                {grr != null && grr > 30
                  ? "Exceeds the 30% rejection threshold — the gauge cannot reliably discriminate parts. Recommend rejecting and re-qualifying the instrument."
                  : "Above the 10% target but acceptable for non-critical characteristics. Manager judgment required."}
              </p>
            </div>
          </div>

          <div className="arad-reveal-sm" style={{ "--d": "260ms" } as React.CSSProperties}>
            <div className="section-label" style={{ marginBottom: 8 }}>Decision</div>
            <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
              {(
                [
                  ["approved", "Approve", "var(--success)", Check],
                  ["rejected", "Reject", "var(--critical)", X],
                ] as const
              ).map(([id, label, color, IconCmp]) => {
                const sel = decision === id;
                const dimmed = decision !== null && !sel;
                return (
                  <button
                    key={id}
                    onClick={() => setDecision(id)}
                    style={{
                      flex: 1,
                      height: 42,
                      border: `1px solid ${sel ? color : "var(--border-default)"}`,
                      borderRadius: "var(--radius-md)",
                      cursor: "pointer",
                      fontFamily: "var(--font-sans)",
                      fontSize: 13,
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 7,
                      transition: "all 150ms ease-out",
                      background: sel ? (id === "approved" ? "rgba(16,185,129,.14)" : "rgba(239,68,68,.14)") : "transparent",
                      color: sel ? color : "var(--text-muted)",
                      opacity: dimmed ? 0.4 : 1,
                      boxShadow: sel ? `0 0 0 1px ${color}, 0 0 16px -2px ${color}` : "none",
                    }}
                  >
                    <IconCmp size={16} />
                    {label}
                  </button>
                );
              })}
            </div>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add review notes…"
              rows={3}
              className="input-field"
              style={{ resize: "vertical" }}
            />
          </div>
        </div>

        <div style={{ padding: 18, borderTop: "1px solid var(--border-default)", display: "flex", gap: 10 }}>
          <button onClick={close} className="btn btn-ghost">Cancel</button>
          <button
            onClick={() => decision && onSubmit(row, decision, notes)}
            disabled={!decision || submitting}
            className={decision === "rejected" ? "btn btn-danger" : "btn btn-primary"}
            style={{ flex: 1, opacity: decision ? 1 : 0.4 }}
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : null}
            {decision === "rejected" ? "Submit Rejection" : decision === "approved" ? "Submit Approval" : "Select a decision"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ReviewQueuePage() {
  const [rows, setRows] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<ReviewQueueItem | null>(null);
  const [exiting, setExiting] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await getReviews());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the review queue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const overdueCount = useMemo(() => rows.filter((r) => isOverdue(r.due_at)).length, [rows]);

  const handleSubmit = async (row: ReviewQueueItem, decision: "approved" | "rejected", notes: string) => {
    setSubmitting(true);
    try {
      await decideReview(row.id, { decision, notes, decided_by: "quality-engineer" });
      setDrawer(null);
      setExiting((e) => [...e, row.id]);
      setTimeout(() => {
        setRows((rs) => rs.filter((r) => r.id !== row.id));
        setExiting((e) => e.filter((k) => k !== row.id));
      }, 440);
      toast(
        decision === "approved"
          ? { type: "success", title: "Study approved", msg: `${row.equipment_id} accepted · audit entry recorded` }
          : { type: "error", title: "Study rejected", msg: `${row.equipment_id} rejected · re-qualification requested` }
      );
    } catch {
      showToast("Review decision failed. Check the backend connection.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="arad-page min-h-full overflow-y-auto" style={{ background: "var(--bg-root)" }}>
      <div className="mx-auto flex min-h-full max-w-[1400px] flex-col px-6 py-6">
        {/* Page header */}
        <div style={{ display: "flex", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <h1 className="page-title">Review Queue</h1>
            <div className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
              Conditional GR&R studies awaiting manager approval
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <button onClick={() => void load()} className="btn btn-secondary" disabled={loading}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {/* Stats line */}
        <div style={{ display: "flex", gap: 20, marginBottom: 16, fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--text-secondary)" }}>
          <span>
            <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent)", fontWeight: 600 }}>{rows.length}</span> Pending
          </span>
          <span style={{ opacity: 0.4 }}>·</span>
          <span>
            <span style={{ fontFamily: "var(--font-mono)", color: overdueCount ? "var(--critical)" : "var(--text-muted)", fontWeight: 600 }}>
              {overdueCount}
            </span>{" "}
            Overdue
          </span>
        </div>

        <Card padding={0} style={{ overflow: "hidden" }}>
          {loading ? (
            <div className="flex flex-col items-center py-14" style={{ color: "var(--text-muted)" }}>
              <Loader2 size={22} className="mb-2 animate-spin" />
              Loading review queue...
            </div>
          ) : error ? (
            <div className="flex flex-col items-center px-6 py-12 text-center">
              <p className="text-sm" style={{ color: "var(--critical)" }}>{error}</p>
              <button onClick={() => void load()} className="btn btn-secondary mt-4">
                <RefreshCw size={14} /> Retry
              </button>
            </div>
          ) : rows.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--text-muted)" }}>
              All caught up — no pending reviews. Conditional GR&R studies land here automatically.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Equipment", "Characteristic", "%GR&R", "NDC", "Submitted", "Assigned", "Due", "Status", ""].map((c, i) => (
                      <th
                        key={i}
                        style={{
                          textAlign: i === 8 ? "right" : "left",
                          padding: "10px 20px",
                          fontFamily: "var(--font-sans)",
                          fontSize: 11,
                          fontWeight: 600,
                          letterSpacing: ".08em",
                          textTransform: "uppercase",
                          color: "var(--text-muted)",
                          borderBottom: "1px solid var(--border-default)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const overdue = isOverdue(r.due_at);
                    return (
                      <tr key={r.id} className={exiting.includes(r.id) ? "arad-collapse-row" : undefined}>
                        <td style={tdS}><span style={{ fontFamily: "var(--font-mono)" }}>{r.equipment_id}</span></td>
                        <td style={tdS}>{r.characteristic_name}</td>
                        <td style={tdS}>
                          <span style={{ fontFamily: "var(--font-mono)", color: grrColor(r.grr_pct) }}>
                            {r.grr_pct != null ? `${r.grr_pct.toFixed(1)}%` : "—"}
                          </span>
                        </td>
                        <td style={tdS}><span className={ndcBadge(r.ndc)}>{r.ndc ?? "—"}</span></td>
                        <td style={tdS}><span style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>{shortDate(r.created_at)}</span></td>
                        <td style={tdS}>{r.assigned_to || "—"}</td>
                        <td style={tdS}>
                          {overdue ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontFamily: "var(--font-mono)", color: "var(--critical)" }}>
                              <TriangleAlert size={13} />
                              {shortDate(r.due_at)}
                            </span>
                          ) : (
                            <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>{shortDate(r.due_at)}</span>
                          )}
                        </td>
                        <td style={tdS}>
                          {overdue ? <span className="badge badge-critical">Overdue</span> : <span className="badge badge-info">Pending</span>}
                        </td>
                        <td style={{ ...tdS, textAlign: "right" }}>
                          <button onClick={() => setDrawer(r)} className="btn btn-secondary !h-[30px] !px-3 text-xs">
                            Review
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {drawer && <ReviewDrawer row={drawer} onClose={() => setDrawer(null)} onSubmit={(r, d, n) => void handleSubmit(r, d, n)} submitting={submitting} />}
    </div>
  );
}
