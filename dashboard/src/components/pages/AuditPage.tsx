"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, FileText, Loader2, RefreshCw, Search } from "lucide-react";
import HelpTip from "@/components/ui/HelpTip";
import { apiClient, getAuditLog, showToast, type AuditLogItem } from "@/api/apiClient";
import { parseApiDate } from "@/lib/utils";

function formatTimestamp(value: string) {
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [entityFilter, setEntityFilter] = useState("all");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAuditLog();
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the audit log");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const entityTypes = useMemo(() => {
    const types = new Set(entries.map((entry) => entry.entity_type).filter(Boolean));
    return ["all", ...Array.from(types).sort()];
  }, [entries]);

  const filtered = useMemo(() => {
    return entries.filter((entry) => {
      if (entityFilter !== "all" && entry.entity_type !== entityFilter) {
        return false;
      }

      if (search) {
        const haystack = `${entry.action} ${entry.actor} ${entry.entity_type} ${entry.entity_id}`.toLowerCase();
        if (!haystack.includes(search.toLowerCase())) {
          return false;
        }
      }

      return true;
    });
  }, [entries, search, entityFilter]);

  const exportCsv = async () => {
    setExporting(true);
    try {
      const blob = await apiClient.getFile("/api/v1/audit-log/export");
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
      anchor.click();
      window.URL.revokeObjectURL(url);
      showToast("Audit log exported.");
    } catch {
      showToast("Audit export failed. Check the backend connection.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="min-h-full overflow-y-auto px-4 py-6 md:px-6" style={{ background: "var(--bg-root)" }}>
      <div className="mx-auto flex max-w-6xl flex-col gap-5">
        {/* Header */}
        <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="page-title">Audit Trail</h1>
              <HelpTip text="An automatic, tamper-proof log of every action in the app — who did what, and when. It's here for audits and traceability. There's nothing to set up; it records on its own." />
            </div>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Complete, immutable record of every quality workflow action — required for compliance reviews.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => void load()} className="btn btn-secondary" disabled={loading}>
              <RefreshCw size={14} /> Refresh
            </button>
            <button onClick={() => void exportCsv()} className="btn btn-primary" disabled={exporting || !entries.length}>
              {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              Export CSV
            </button>
          </div>
        </header>

        {/* Filters */}
        <div className="panel flex flex-wrap items-center gap-3 px-5 py-3.5">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-ghost)" }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search action, actor, or entity..."
              className="input-field !w-64 !pl-9"
            />
          </div>
          <select
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
            className="input-field !w-auto cursor-pointer"
            aria-label="Filter by entity type"
          >
            {entityTypes.map((type) => (
              <option key={type} value={type}>
                {type === "all" ? "All entity types" : type}
              </option>
            ))}
          </select>
          <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
            {filtered.length} of {entries.length} entries
          </span>
        </div>

        {/* Table */}
        {loading ? (
          <div className="flex flex-col items-center py-16" style={{ color: "var(--text-muted)" }}>
            <Loader2 size={22} className="mb-2 animate-spin" />
            Loading audit log...
          </div>
        ) : error ? (
          <div className="panel flex flex-col items-center px-6 py-12 text-center">
            <p className="text-sm" style={{ color: "var(--critical)" }}>{error}</p>
            <button onClick={() => void load()} className="btn btn-secondary mt-4">
              <RefreshCw size={14} /> Retry
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div
            className="flex flex-col items-center rounded-lg border border-dashed px-6 py-14 text-center"
            style={{ borderColor: "var(--border-default)", background: "var(--bg-surface)" }}
          >
            <FileText size={22} style={{ color: "var(--text-ghost)" }} />
            <p className="mt-3 text-sm font-medium" style={{ color: "var(--text-primary)" }}>No audit entries found</p>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Entries appear automatically as GR&R studies, SPC analyses, and alert actions run.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--border-subtle)" }}>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Entity</th>
                    <th>Actor</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody style={{ background: "var(--bg-surface)" }}>
                  {filtered.slice(0, 200).map((entry) => (
                    <tr key={entry.id}>
                      <td className="whitespace-nowrap" style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>
                        {formatTimestamp(entry.timestamp)}
                      </td>
                      <td style={{ color: "var(--text-primary)", fontWeight: 500 }}>{entry.action}</td>
                      <td>
                        <span className="badge badge-neutral">{entry.entity_type}</span>
                        <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>{entry.entity_id}</span>
                      </td>
                      <td>{entry.actor || "system"}</td>
                      <td
                        className="max-w-[280px] truncate text-xs"
                        style={{ color: "var(--text-muted)" }}
                        title={entry.details ? JSON.stringify(entry.details) : undefined}
                      >
                        {entry.details ? JSON.stringify(entry.details) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
