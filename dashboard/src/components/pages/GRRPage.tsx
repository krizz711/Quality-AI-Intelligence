"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ChevronRight,
  ClipboardPaste,
  Download,
  FileUp,
  Gauge,
  Keyboard,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Sparkles,
  Table2,
  Upload,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import {
  showToast,
  submitGRRAnalysis,
  type GRRAnalysisResponse,
  type GRRInputMeasurement,
} from "@/api/apiClient";
import { grrVerdict } from "@/lib/utils";
import { useAppStore } from "@/lib/store";

type Step = 1 | 2 | 3;

type MeasurementRow = GRRInputMeasurement;

type GRRFormValues = {
  operators: number;
  parts: number;
  trials: number;
  partTolerance?: number;
  processName: string;
  measurements: MeasurementRow[];
};

type AnalysisState = {
  result: GRRAnalysisResponse | null;
  loading: boolean;
  error: string | null;
};

const stepLabels = ["Setup", "Data Entry", "Analysis"] as const;

const defaultValues: GRRFormValues = {
  operators: 3,
  parts: 10,
  trials: 2,
  processName: "",
  partTolerance: undefined,
  measurements: [],
};

const inputClass = "input-field";

function formatTimestamp(date: Date | string) {
  const value = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

function getGaugeColor(pct: number) {
  if (pct < 10) return "#22c55e";
  if (pct <= 30) return "#eab308";
  return "#ef4444";
}

function parseCsv(text: string) {
  const rows = text
    .trim()
    .split(/\r?\n/)
    .filter(Boolean);

  if (rows.length < 2) {
    throw new Error("CSV needs a header row and at least one data row");
  }

  const headers = rows[0].split(",").map((value) => value.trim().toLowerCase());
  const required = ["operator", "part", "trial", "value"];
  for (const header of required) {
    if (!headers.includes(header)) {
      throw new Error(`CSV must include ${required.join(", ")} columns`);
    }
  }

  return rows.slice(1).map((row) => {
    const cells = row.split(",").map((value) => value.trim());
    const record: Record<string, string> = {};

    headers.forEach((header, index) => {
      record[header] = cells[index] ?? "";
    });

    return {
      operator: record.operator,
      part: Number(record.part),
      trial: Number(record.trial),
      value: Number(record.value),
    };
  });
}

/**
 * Parse an arbitrary block pasted from Excel/Sheets into an ordered list of
 * numeric values. Handles tab-, comma-, semicolon- and whitespace-separated
 * cells across multiple rows; non-numeric cells (e.g. stray headers) are dropped.
 */
function parseClipboardNumbers(text: string): number[] {
  return text
    .replace(/ /g, " ")
    .trim()
    .split(/\r?\n/)
    .flatMap((line) => line.split(/[\t,;\s]+/))
    .map((cell) => cell.trim())
    .filter((cell) => cell.length > 0)
    .map((cell) => Number(cell))
    .filter((value) => Number.isFinite(value));
}

function createMeasurementRows(operators: number, parts: number, trials: number) {
  const rows: MeasurementRow[] = [];

  for (let operatorIndex = 1; operatorIndex <= operators; operatorIndex += 1) {
    for (let partIndex = 1; partIndex <= parts; partIndex += 1) {
      for (let trialIndex = 1; trialIndex <= trials; trialIndex += 1) {
        rows.push({
          operator: `Operator ${operatorIndex}`,
          part: partIndex,
          trial: trialIndex,
          value: "" as unknown as number,
        });
      }
    }
  }

  return rows;
}

function computeGrandMean(measurements: MeasurementRow[]) {
  const values = measurements.map((row) => row.value).filter((value) => Number.isFinite(value));
  if (!values.length) {
    return null;
  }

  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function GaugeChart({ value }: { value: number }) {
  const clamped = Math.min(Math.max(value, 0), 100);
  const angle = -90 + (clamped / 100) * 180;
  const color = getGaugeColor(clamped);

  return (
    <div className="relative mx-auto h-40 w-40">
      {/* verdict-tinted halo */}
      <motion.div
        className="absolute inset-2 rounded-full"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.6 }}
        style={{ boxShadow: `0 0 70px -8px ${color}66, inset 0 0 40px -16px ${color}55` }}
      />
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background:
            "conic-gradient(from 180deg, #22c55e 0deg 36deg, #eab308 36deg 108deg, #ef4444 108deg 180deg, transparent 180deg 360deg)",
          mask: "radial-gradient(circle at center, transparent 54%, black 55%)",
          WebkitMask: "radial-gradient(circle at center, transparent 54%, black 55%)",
        }}
      />
      <div className="absolute inset-6 rounded-full bg-[var(--bg-root)] shadow-inner shadow-black/60" />
      {/* Animated needle */}
      <motion.div
        className="absolute left-1/2 top-1/2 h-[68px] w-0.5 origin-bottom rounded-full bg-[var(--text-primary)]"
        style={{ x: "-50%", y: "-100%" }}
        initial={{ rotate: -90 }}
        animate={{ rotate: angle }}
        transition={{ type: "spring", stiffness: 80, damping: 18, delay: 0.25 }}
      />
      <motion.div
        className="absolute left-1/2 top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--bg-root)]"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.2 }}
        style={{ background: color }}
      />
      <div className="absolute inset-x-0 bottom-7 text-center">
        <motion.div
          className="text-3xl font-semibold tabular-nums"
          style={{ color, textShadow: `0 0 26px ${color}55` }}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          {clamped.toFixed(1)}%
        </motion.div>
        <div className="mt-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--text-muted)]">GR&amp;R</div>
      </div>
    </div>
  );
}

function StepBadge({ step, active }: { step: number; active: boolean }) {
  return (
    <div
      className="flex h-9 w-9 items-center justify-center rounded-full border font-mono text-sm font-semibold transition-all duration-200"
      style={
        active
          ? {
              borderColor: "rgba(130,174,255,0.45)",
              background: "var(--gradient-accent)",
              color: "white",
              boxShadow: "0 0 18px -4px rgba(78,140,255,0.7), inset 0 1px 0 rgba(255,255,255,0.25)",
            }
          : { borderColor: "var(--border-strong)", background: "var(--bg-elevated)", color: "var(--text-muted)" }
      }
    >
      {step}
    </div>
  );
}

export default function GRRPage() {
  const [step, setStep] = useState<Step>(1);
  const [analysis, setAnalysis] = useState<AnalysisState>({ result: null, loading: false, error: null });
  const [tableReady, setTableReady] = useState(false);
  const [importing, setImporting] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const {
    register,
    control,
    handleSubmit,
    trigger,
    getValues,
    setValue,
    formState: { errors },
  } = useForm<GRRFormValues>({
    defaultValues,
    mode: "onBlur",
  });

  const { fields, replace } = useFieldArray({
    control,
    name: "measurements",
  });

  const measurements = useWatch({ control, name: "measurements" });
  const grandMean = useMemo(() => computeGrandMean(measurements || []), [measurements]);
  const currentAnalysis = analysis.result;
  const verdict = currentAnalysis ? grrVerdict(currentAnalysis.grr_percent) : null;
  const analysisPct = currentAnalysis?.grr_percent ?? 0;

  const operators = useWatch({ control, name: "operators" });
  const parts = useWatch({ control, name: "parts" });
  const trials = useWatch({ control, name: "trials" });
  const processName = useWatch({ control, name: "processName" });
  const partTolerance = useWatch({ control, name: "partTolerance" });
  const { grrPrefill, setGrrPrefill } = useAppStore();

  // Prefill from the Gage Registry "Run GR&R study" action.
  useEffect(() => {
    if (!grrPrefill) return;
    if (grrPrefill.processName) setValue("processName", grrPrefill.processName);
    if (grrPrefill.partTolerance != null) setValue("partTolerance", grrPrefill.partTolerance);
    setGrrPrefill(null);
    showToast(`Loaded ${grrPrefill.processName ?? "gage"} into the study setup.`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const step1Valid = async () => {
    return trigger(["operators", "parts", "trials", "processName", "partTolerance"]);
  };

  const generateTable = async () => {
    const valid = await step1Valid();
    if (!valid) {
      return;
    }

    const values = getValues();
    const rows = createMeasurementRows(values.operators, values.parts, values.trials);
    replace(rows);
    setTableReady(true);
    setStep(2);
    setAnalysis({ result: null, loading: false, error: null });
  };

  const fillMeasurementsFromCsv = async (file: File) => {
    setImporting(true);
    try {
      const text = await file.text();
      const importedRows = parseCsv(text);

      if (!fields.length) {
        throw new Error("Generate the measurement table before importing CSV data");
      }

      const nextRows = fields.map((field) => {
        const match = importedRows.find(
          (row) =>
            (row.operator === field.operator || `Operator ${row.operator}` === field.operator) &&
            row.part === field.part &&
            row.trial === field.trial,
        );
        return {
          operator: field.operator,
          part: field.part,
          trial: field.trial,
          value: match?.value ?? ("" as unknown as number),
        };
      });

      replace(nextRows);
      showToast("CSV imported into the measurement table.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "CSV import failed");
    } finally {
      setImporting(false);
    }
  };

  /** Fill the measurement grid in display order from a flat list of values. */
  const applyFlatValues = (values: number[]) => {
    if (!fields.length) {
      showToast("Generate the measurement table before pasting values.");
      return;
    }
    if (!values.length) {
      showToast("No numeric values found to paste.");
      return;
    }
    const current = getValues("measurements");
    const next = current.map((row, index) => ({
      ...row,
      value: index < values.length && Number.isFinite(values[index]) ? values[index] : row.value,
    }));
    replace(next);
    if (values.length > fields.length) {
      showToast(`Filled ${fields.length} cells · ${values.length - fields.length} extra value(s) ignored.`);
    } else {
      showToast(`Filled ${values.length} of ${fields.length} cells.`);
    }
  };

  const applyPaste = (text: string) => {
    applyFlatValues(parseClipboardNumbers(text));
    setShowPaste(false);
    setPasteText("");
  };

  /** Seed the grid with realistic, well-behaved sample data for demos/onboarding. */
  const loadSampleData = () => {
    if (!fields.length) {
      showToast("Generate the measurement table first.");
      return;
    }
    const current = getValues("measurements");
    const next = current.map((row) => {
      const opNum = Number(/(\d+)/.exec(row.operator)?.[1] ?? 1);
      const partBase = 10 + (Number(row.part) - 1) * 0.5;
      const opBias = (opNum - 1) * 0.03;
      const noise = (Math.random() - 0.5) * 0.05;
      return { ...row, value: Number((partBase + opBias + noise).toFixed(3)) };
    });
    replace(next);
    showToast("Loaded sample measurement data.");
  };

  /** Move keyboard focus between measurement cells (arrow keys / Enter). */
  const focusCell = (index: number) => {
    if (index < 0) return;
    const el = document.getElementById(`grr-value-${index}`) as HTMLInputElement | null;
    if (el) {
      el.focus();
      el.select();
    }
  };

  const runAnalysis = async (values: GRRFormValues) => {
    if (!values.measurements.length) {
      setAnalysis({ result: null, loading: false, error: "Generate the measurement table first." });
      return;
    }

    const payload = {
      measurements: values.measurements.map((row) => ({
        operator: row.operator,
        part: row.part,
        trial: row.trial,
        value: row.value,
      })),
      part_tolerance: values.partTolerance,
      process_name: values.processName || undefined,
    };

    setAnalysis({ result: null, loading: true, error: null });
    setStep(3);

    try {
      const result = await submitGRRAnalysis(payload);
      setAnalysis({ result, loading: false, error: null });
      setLastSavedAt(new Date());
    } catch (error) {
      setAnalysis({
        result: null,
        loading: false,
        error: error instanceof Error ? error.message : "GR&R analysis failed",
      });
    }
  };

  const retryAnalysis = () => {
    void handleSubmit(runAnalysis)();
  };

  const saveToHistory = () => {
    showToast("Analysis already saved to history by the backend.");
    setLastSavedAt(new Date());
  };

  const [exportingPdf, setExportingPdf] = useState(false);

  const exportPdf = async () => {
    if (!currentAnalysis) {
      toast("Run an analysis before exporting the report.");
      return;
    }

    setExportingPdf(true);
    const toastId = toast.loading("Generating PDF report…");

    try {
      const [{ pdf }, { GRRPdfReport }] = await Promise.all([
        import("@react-pdf/renderer"),
        import("@/components/reports/GRRPdfReport"),
      ]);

      const blob = await pdf(
        GRRPdfReport({
          analysis: currentAnalysis,
          processName: processName || "Unnamed Process",
          operators,
          parts,
          trials,
          partTolerance,
        })
      ).toBlob();

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `grr-${(processName || "report").toLowerCase().replace(/\s+/g, "-")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);

      toast.success("Report downloaded.", { id: toastId });
    } catch (err) {
      console.error("PDF generation failed:", err);
      toast.error("PDF generation failed. Check console for details.", { id: toastId });
    } finally {
      setExportingPdf(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto px-6 py-7 md:px-10 lg:py-9" style={{ color: "var(--text-primary)" }}>
      <div className="mx-auto flex max-w-[1500px] flex-col gap-7">
        <header className="surface-card px-7 py-7 lg:px-9 lg:py-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-4">
                <div
                  className="flex h-12 w-12 items-center justify-center rounded-2xl border"
                  style={{
                    borderColor: "var(--accent-bg-strong)",
                    background: "var(--accent-bg)",
                    color: "var(--accent-bright)",
                    boxShadow: "0 0 28px -6px rgba(78,140,255,0.55), inset 0 1px 0 rgba(255,255,255,0.1)",
                  }}
                >
                  <Sparkles size={22} />
                </div>
                <div>
                  <div className="kicker mb-2" style={{ color: "var(--accent-bright)" }}>
                    Measurement Systems Analysis
                  </div>
                  <h1 className="text-display gradient-text text-[26px] font-semibold md:text-[33px]">GR&amp;R Study Wizard</h1>
                  <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                    Three-step measurement system analysis with live calculations and AI review.
                  </p>
                </div>
              </div>
            </div>
            <div className="panel-inset px-4 py-3">
              <div className="section-label text-[10px]">Current status</div>
              <div className="mt-1.5 flex items-center gap-2.5 text-sm font-semibold" style={{ color: "var(--success-text)" }}>
                <span className="live-dot" style={{ width: 7, height: 7 }} />
                Ready for measurement entry
              </div>
              <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                {lastSavedAt ? `Last saved ${formatTimestamp(lastSavedAt)}` : "Analysis not yet run"}
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            {stepLabels.map((label, index) => (
              <div
                key={label}
                className="flex items-center gap-3 rounded-xl border px-4 py-3 transition-colors duration-200"
                style={
                  step === index + 1
                    ? {
                        borderColor: "rgba(78,140,255,0.28)",
                        background: "linear-gradient(180deg, rgba(78,140,255,0.12), rgba(78,140,255,0.04))",
                        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
                      }
                    : { borderColor: "var(--border-subtle)", background: "rgba(9,13,20,0.5)" }
                }
              >
                <StepBadge step={index + 1} active={step === index + 1} />
                <div>
                  <div className="font-mono text-[9.5px] uppercase tracking-[0.18em]" style={{ color: "var(--text-ghost)" }}>
                    Step {index + 1}
                  </div>
                  <div
                    className="text-sm font-semibold"
                    style={{ color: step === index + 1 ? "var(--text-primary)" : "var(--text-secondary)" }}
                  >
                    {label}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </header>

        <form onSubmit={handleSubmit(runAnalysis)} className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,0.55fr)]">
          <div className="min-w-0 space-y-6">
            <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.section
                key="step1"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
                className="surface-card p-6"
              >
                <SectionHeader
                  icon={<Wand2 size={16} />}
                  title="Step 1 - Setup"
                  description="Define the study size and process metadata before generating the table."
                />

                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <Field label="Number of Operators" error={errors.operators?.message}>
                    <input
                      type="number"
                      min={2}
                      max={10}
                      {...register("operators", {
                        valueAsNumber: true,
                        required: "Enter operator count",
                        min: { value: 2, message: "Minimum 2 operators" },
                        max: { value: 10, message: "Maximum 10 operators" },
                      })}
                      className={inputClass}
                    />
                  </Field>

                  <Field label="Number of Parts" error={errors.parts?.message}>
                    <input
                      type="number"
                      min={5}
                      max={25}
                      {...register("parts", {
                        valueAsNumber: true,
                        required: "Enter part count",
                        min: { value: 5, message: "Minimum 5 parts" },
                        max: { value: 25, message: "Maximum 25 parts" },
                      })}
                      className={inputClass}
                    />
                  </Field>

                  <Field label="Number of Trials" error={errors.trials?.message}>
                    <input
                      type="number"
                      min={2}
                      max={3}
                      {...register("trials", {
                        valueAsNumber: true,
                        required: "Enter trial count",
                        min: { value: 2, message: "Minimum 2 trials" },
                        max: { value: 3, message: "Maximum 3 trials" },
                      })}
                      className={inputClass}
                    />
                  </Field>

                  <Field label="Part Tolerance" error={errors.partTolerance?.message} optional>
                    <input
                      type="number"
                      step="0.0001"
                      {...register("partTolerance", {
                        setValueAs: (value) => (value === "" || value === null ? undefined : Number(value)),
                        min: { value: 0, message: "Tolerance must be positive" },
                      })}
                      className={inputClass}
                      placeholder="Optional"
                    />
                  </Field>

                  <Field className="md:col-span-2" label="Process Name" error={errors.processName?.message}>
                    <input
                      type="text"
                      placeholder="e.g. Bore Diameter"
                      {...register("processName", {
                        required: "Process name is required",
                        minLength: { value: 2, message: "Process name is too short" },
                      })}
                      className={inputClass}
                    />
                  </Field>
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => void generateTable()}
                    className="btn btn-primary"
                  >
                    <Table2 size={16} /> Generate Measurement Table
                  </button>
                  <div className="text-xs text-[var(--text-muted)]">Defaults: 3 operators, 10 parts, 2 trials</div>
                </div>
              </motion.section>
            )}

            {step === 2 && (
              <motion.section
                key="step2"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
                className="surface-card p-6"
              >
                <SectionHeader
                  icon={<FileUp size={16} />}
                  title="Step 2 - Data Entry"
                  description="Fill every measurement cell, import CSV data, and preview the grand mean live."
                />

                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 panel-inset px-4 py-3">
                  <div className="text-sm text-[var(--text-secondary)]">
                    <span className="font-semibold text-[var(--text-primary)]">{processName || "Unnamed process"}</span>
                    <span className="text-[var(--text-muted)]">
                      {" "}
                      · {operators} operators · {parts} parts · {trials} trials
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <button
                      type="button"
                      onClick={() => setShowPaste((value) => !value)}
                      className="btn btn-secondary h-8 px-3 text-xs"
                    >
                      <ClipboardPaste size={14} /> Paste from Excel
                    </button>
                    <label className="btn btn-secondary h-8 cursor-pointer px-3 text-xs">
                      {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                      Import CSV
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        className="hidden"
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          if (file) {
                            void fillMeasurementsFromCsv(file);
                          }
                          event.currentTarget.value = "";
                        }}
                      />
                    </label>
                    <button
                      type="button"
                      onClick={loadSampleData}
                      className="btn btn-ghost h-8 px-3 text-xs"
                    >
                      <Sparkles size={14} /> Load sample
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        const valid = await trigger("measurements");
                        if (valid) setStep(3);
                        else showToast("Please fill out all measurements before proceeding.");
                      }}
                      className="btn btn-secondary h-8 px-3 text-xs"
                    >
                      Review Analysis Step <ChevronRight size={14} />
                    </button>
                  </div>
                </div>

                <AnimatePresence>
                  {showPaste && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-4 overflow-hidden"
                    >
                      <div className="panel-inset p-4">
                        <div className="mb-2 flex items-center gap-2">
                          <ClipboardPaste size={14} className="text-[var(--accent-bright)]" />
                          <span className="section-label">Paste measurement values</span>
                        </div>
                        <p className="mb-3 text-xs leading-5 text-[var(--text-muted)]">
                          Copy a column or block of values from Excel/Sheets and paste below. Values fill the table
                          top-to-bottom in display order — Operator 1 (all parts × trials), then Operator 2, and so on.
                          <span className="text-[var(--text-secondary)]"> {fields.length} cells expected.</span>
                        </p>
                        <textarea
                          value={pasteText}
                          onChange={(event) => setPasteText(event.target.value)}
                          onPaste={(event) => {
                            const text = event.clipboardData.getData("text");
                            if (text) {
                              event.preventDefault();
                              applyPaste(text);
                            }
                          }}
                          placeholder="Paste here (Ctrl+V / ⌘V)…"
                          rows={4}
                          spellCheck={false}
                          className="input-field stat-number text-xs"
                        />
                        <div className="mt-3 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => applyPaste(pasteText)}
                            className="btn btn-primary h-8 px-3 text-xs"
                          >
                            Apply values
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setPasteText("");
                              setShowPaste(false);
                            }}
                            className="btn btn-ghost h-8 px-3 text-xs"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="mt-5 panel-inset p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] text-[var(--text-muted)]">Grand Mean Preview</div>
                      <div className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
                        {grandMean !== null ? grandMean.toFixed(4) : "—"}
                      </div>
                    </div>
                    <div className="text-right text-xs text-[var(--text-muted)]">Live preview updates as values are entered</div>
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-1.5 text-[11px] text-[var(--text-ghost)]">
                  <Keyboard size={12} />
                  <span>Use ↑ ↓ or Enter to move between cells · paste from Excel to fill all at once</span>
                </div>

                <div className="mt-3 overflow-hidden rounded-xl border border-[var(--border-default)]">
                  <div className="max-h-[520px] overflow-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead className="sticky top-0 z-10 bg-[var(--bg-elevated)] font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--text-muted)]">
                        <tr>
                          <th className="px-4 py-3 font-medium">Operator</th>
                          <th className="px-4 py-3 font-medium">Part #</th>
                          <th className="px-4 py-3 font-medium">Trial #</th>
                          <th className="px-4 py-3 font-medium">Measurement Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[rgba(148,163,184,0.07)]">
                        {fields.map((field, index) => (
                          <tr key={field.id} className="transition hover:bg-[var(--bg-hover)]">
                            <td className="px-4 py-3 text-[var(--text-secondary)]">{field.operator}</td>
                            <td className="px-4 py-3 text-[var(--text-secondary)]">{field.part}</td>
                            <td className="px-4 py-3 text-[var(--text-secondary)]">{field.trial}</td>
                            <td className="px-4 py-3">
                              <input
                                id={`grr-value-${index}`}
                                type="number"
                                step="0.0001"
                                {...register(`measurements.${index}.value`, {
                                  valueAsNumber: true,
                                  required: "Measurement is required",
                                  validate: (v) => !Number.isNaN(v) || "Required",
                                })}
                                onKeyDown={(event) => {
                                  if (event.key === "Enter" || event.key === "ArrowDown") {
                                    event.preventDefault();
                                    focusCell(index + 1);
                                  } else if (event.key === "ArrowUp") {
                                    event.preventDefault();
                                    focusCell(index - 1);
                                  }
                                }}
                                className={`${inputClass} stat-number ${errors.measurements?.[index]?.value ? "input-error" : ""}`}
                                placeholder="Enter value"
                              />
                            </td>
                          </tr>
                        ))}
                        {!fields.length ? (
                          <tr>
                            <td className="px-4 py-10 text-center text-[var(--text-muted)]" colSpan={4}>
                              Generate the measurement table to begin data entry.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="btn btn-secondary"
                  >
                    <ArrowLeft size={16} /> Back to Setup
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      const valid = await trigger("measurements");
                      if (valid) setStep(3);
                      else showToast("Please fill out all measurements before proceeding.");
                    }}
                    className="btn btn-primary"
                  >
                    Proceed to Analysis <ArrowRight size={16} />
                  </button>
                </div>
              </motion.section>
            )}

            {step === 3 && (
              <motion.section
                key="step3"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
                className="surface-card p-6"
              >
                <SectionHeader
                  icon={<Gauge size={16} />}
                  title="Step 3 - Analysis"
                  description="Run the backend GR&R analysis, then review the verdict and AI commentary."
                />

                <div className="mt-6 flex flex-wrap items-center gap-3">
                  <button
                    type="submit"
                    disabled={analysis.loading}
                    className="btn btn-primary"
                  >
                    {analysis.loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
                    Run GR&R Analysis
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="btn btn-secondary"
                  >
                    <ArrowLeft size={16} /> Back to Data Entry
                  </button>
                  <div className="text-xs text-[var(--text-muted)]">{measurements?.length || 0} measurements ready for analysis</div>
                </div>

                {analysis.error && (
                  <div className="mt-5 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-200">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold">Analysis failed</div>
                        <div className="mt-1 text-rose-100/90">{analysis.error}</div>
                      </div>
                      <button
                        type="button"
                        onClick={retryAnalysis}
                        className="inline-flex items-center gap-2 rounded-xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-100 transition hover:bg-rose-400/20"
                      >
                        <RefreshCw size={14} /> Retry
                      </button>
                    </div>
                  </div>
                )}

                {analysis.loading && (
                  <div className="mt-5 flex items-center gap-3 panel-inset px-4 py-4 text-sm text-[var(--text-secondary)]">
                    <Loader2 size={16} className="animate-spin text-emerald-300" />
                    Running statistical analysis on the backend...
                  </div>
                )}

                {currentAnalysis && verdict && (
                  <motion.div
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 260, damping: 28 }}
                    className="mt-6 space-y-5"
                  >
                    <div className="grid gap-3 sm:grid-cols-4">
                      <div className="elevated-card aura grain flex flex-col items-center justify-center p-5 sm:row-span-1">
                        <GaugeChart value={analysisPct} />
                        <div className="mt-3 flex items-center justify-center">
                          <span
                            className={`badge h-8 px-4 text-[12px] ${
                              currentAnalysis.grr_percent < 10
                                ? "badge-success"
                                : currentAnalysis.grr_percent <= 30
                                  ? "badge-warning"
                                  : "badge-critical"
                            }`}
                          >
                            {verdict.label}
                          </span>
                        </div>
                      </div>
                      {[
                        { label: "Repeatability · EV σ", value: currentAnalysis.repeatability.toFixed(4), tone: "text-emerald-300" },
                        { label: "Reproducibility · AV σ", value: currentAnalysis.reproducibility.toFixed(4), tone: "text-amber-300" },
                        { label: "Distinct Categories", value: String(currentAnalysis.number_of_distinct_categories), tone: "text-sky-300" },
                      ].map((metric) => (
                        <div key={metric.label} className="panel-inset p-4">
                          <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-[var(--text-muted)]">{metric.label}</div>
                          <div className={`stat-number mt-2 text-2xl ${metric.tone}`}>{metric.value}</div>
                        </div>
                      ))}
                    </div>

                    <div className="panel-inset rounded-xl p-5">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="section-label">AI Analysis</h3>
                        <span className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">
                          {formatTimestamp(currentAnalysis.timestamp)}
                        </span>
                      </div>
                      <p className="mt-4 whitespace-pre-line break-words text-sm leading-6 text-[var(--text-secondary)]">{currentAnalysis.ai_analysis}</p>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        onClick={saveToHistory}
                        className="btn btn-secondary"
                      >
                        <Save size={16} /> Save to History
                      </button>
                      <button
                        type="button"
                        onClick={() => void exportPdf()}
                        disabled={exportingPdf}
                        className="btn btn-secondary"
                      >
                        {exportingPdf
                          ? <><Loader2 size={16} className="animate-spin" /> Generating…</>
                          : <><Download size={16} /> Export PDF Report</>}
                      </button>
                      <button
                        type="button"
                        onClick={() => setStep(2)}
                        className="btn btn-primary"
                      >
                        <Plus size={16} /> Adjust Measurements
                      </button>
                    </div>
                  </motion.div>
                )}

                {!analysis.loading && !currentAnalysis && !analysis.error && (
                  <div className="mt-6 overflow-hidden rounded-xl border border-dashed border-[var(--border-strong)] bg-[rgba(9,13,20,0.5)] px-6 py-8 text-center">
                    <img
                      src="/brand/gauge_square.png"
                      alt="Precision measurement gauge"
                      width={132}
                      height={132}
                      className="mx-auto h-[132px] w-[132px] object-contain opacity-95 [filter:drop-shadow(0_12px_28px_rgba(78,140,255,0.25))]"
                    />
                    <h3 className="mt-3 text-sm font-semibold text-[var(--text-primary)]">Ready to analyze</h3>
                    <p className="mt-1 text-sm text-[var(--text-muted)]">Run the GR&R calculation after confirming the table data.</p>
                  </div>
                )}
              </motion.section>
            )}
            </AnimatePresence>
          </div>

          <aside className="min-w-0 space-y-6">
            <div className="surface-card p-5">
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className="text-[var(--text-secondary)]" />
                <h2 className="section-label">Study Summary</h2>
              </div>

              <div className="mt-4 grid gap-3">
                {[
                  { label: "Operators", value: operators },
                  { label: "Parts", value: parts },
                  { label: "Trials", value: trials },
                  { label: "Tolerance", value: partTolerance ?? "Optional" },
                  { label: "Process", value: processName || "Not set" },
                  { label: "Measurements", value: fields.length },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between panel-inset px-4 py-3 text-sm"
                  >
                    <span className="text-[var(--text-muted)]">{item.label}</span>
                    <span className="font-semibold text-[var(--text-primary)]">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-card p-5">
              <div className="flex items-center gap-2">
                <Table2 size={16} className="text-[var(--text-secondary)]" />
                <h2 className="section-label">Data Integrity</h2>
              </div>

              <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
                <div className="flex items-center justify-between panel-inset px-4 py-3">
                  <span className="text-[var(--text-muted)]">Entered values</span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {measurements?.filter((row) => Number.isFinite(row.value)).length || 0}/{fields.length}
                  </span>
                </div>
                <div className="flex items-center justify-between panel-inset px-4 py-3">
                  <span className="text-[var(--text-muted)]">Grand mean</span>
                  <span className="font-semibold text-[var(--text-primary)]">{grandMean !== null ? grandMean.toFixed(4) : "—"}</span>
                </div>
                <div className="flex items-center justify-between panel-inset px-4 py-3">
                  <span className="text-[var(--text-muted)]">Analysis ready</span>
                  <span className="font-semibold text-emerald-300">{tableReady ? "Yes" : "No"}</span>
                </div>
              </div>
            </div>
          </aside>
        </form>
      </div>
    </div>
  );
}

function SectionHeader({
  icon,
  title,
  description,
}: {
  icon: ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] text-[var(--accent-bright)]">
          {icon}
        </div>
        <h2 className="section-label">{title}</h2>
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
    </div>
  );
}

function Field({
  label,
  error,
  children,
  optional = false,
  className = "",
}: {
  label: string;
  error?: string;
  children: ReactNode;
  optional?: boolean;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <div className="mb-2 flex items-center justify-between gap-2 text-sm">
        <span className="font-medium text-[var(--text-primary)]">{label}</span>
        {optional ? <span className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Optional</span> : null}
      </div>
      {children}
      {error ? <div className="mt-2 text-xs text-rose-300">{error}</div> : null}
    </label>
  );
}
