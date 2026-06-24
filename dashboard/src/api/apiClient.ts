"use client";

import { useEffect, useState } from "react";
import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";

export interface BackendErrorResponse {
  error?: boolean;
  message?: string;
  code?: string;
  detail?: string;
}

export interface ApiError {
  message: string;
  code?: string;
  detail?: string;
}

export interface GRRInputMeasurement {
  operator: string;
  part: number;
  trial: number;
  value: number;
}

export interface GRRInput {
  measurements: GRRInputMeasurement[];
  part_tolerance?: number;
  process_name?: string;
}

export interface GRRAnalysisResponse {
  grr_percent: number;
  repeatability: number;
  reproducibility: number;
  number_of_distinct_categories: number;
  ai_analysis: string;
  timestamp: string;
}

export interface GRRHistoryItem {
  id: string;
  timestamp: string;
  grr_percent: number | null;
  verdict: "pass" | "acceptable" | "fail";
  operator_count: number;
  part_count: number;
  process_name?: string | null;
}

export interface SPCInput {
  process_name: string;
  measurements: number[];
  ucl?: number;
  lcl?: number;
  target?: number;
  /** Values to persist as new rows; [] = stats-only recompute; omitted = persist all. */
  new_values?: number[];
}

export interface SPCViolation {
  rule: string;
  index: number;
  value: number;
  description: string;
}

export interface SPCDataResponse {
  mean: number;
  std_dev: number;
  ucl: number;
  lcl: number;
  violations: SPCViolation[];
  ai_analysis: string;
}

export interface SPCHistoryItem {
  timestamp: string;
  value: number;
  part_number?: string | null;
  characteristic_name?: string | null;
}

export interface SPCHistoryResponse {
  process_name: string;
  points: SPCHistoryItem[];
}

export interface SPCProcessSummary {
  name: string;
  points: number;
  latest: string | null;
}

export interface SPCProcessListResponse {
  processes: SPCProcessSummary[];
}

export interface DashboardSummaryResponse {
  total_grr_analyses: number;
  passing_rate: number;
  active_alerts_count: number;
  recent_violations: Array<Record<string, unknown>>;
  last_updated: string;
}

export interface AlertFilters {
  status?: "active" | "resolved";
  severity?: "critical" | "high" | "medium" | "low";
  limit?: number;
}

export interface AlertItem {
  id: string;
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  process_name: string;
  status: "active" | "resolved" | "acknowledged";
  created_at: string;
  resolved_at?: string | null;
  resolved_by?: string | null;
}

export interface AlertListResponse {
  items: AlertItem[];
  total: number;
  limit: number;
}

export interface AlertResolveResponse {
  alert_id: string;
  resolved_at: string;
}

export interface AlertFeedbackInput {
  is_relevant: boolean;
  category?: "true_positive" | "false_positive" | "duplicate" | "late" | "missing_context";
  notes?: string;
  submitted_by?: string;
}

export interface AlertFeedbackResponse {
  feedback_id: string;
  alert_id: string;
  is_relevant: boolean;
  created_at: string;
}

export interface AlertAccuracyResponse {
  feedback_count: number;
  relevant_count: number;
  false_positive_count: number;
  accuracy_rate: number | null;
  target_rate: number;
  target_met: boolean | null;
}

export interface AuditLogItem {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: Record<string, unknown> | null;
}

export interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export const API_BASE_URL_STORAGE_KEY = "arad-api-base-url";
export const API_KEY_STORAGE_KEY = "arad-api-key";

export const resolveApiBaseUrl = () => {
  // User override from Settings takes precedence over build-time env values.
  const storedUrl =
    typeof window !== "undefined" ? window.localStorage.getItem(API_BASE_URL_STORAGE_KEY) : null;
  const viteUrl =
    typeof import.meta !== "undefined"
      ? (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL
      : undefined;
  const nextUrl =
    typeof globalThis !== "undefined"
      ? (globalThis as typeof globalThis & {
          process?: { env?: { NEXT_PUBLIC_API_URL?: string } };
        }).process?.env?.NEXT_PUBLIC_API_URL
      : undefined;

  // In the browser, default to the same-origin Next.js proxy (/api/backend):
  // the API key stays server-side and no CORS configuration is needed.
  if (typeof window !== "undefined") {
    return storedUrl || viteUrl || nextUrl || "/api/backend";
  }

  return viteUrl || nextUrl || "http://127.0.0.1:8000";
};

export const resolveApiKey = () => {
  const storedKey =
    typeof window !== "undefined" ? window.localStorage.getItem(API_KEY_STORAGE_KEY) : null;
  const envKey =
    typeof globalThis !== "undefined"
      ? (globalThis as typeof globalThis & {
          process?: { env?: { NEXT_PUBLIC_API_KEY?: string } };
        }).process?.env?.NEXT_PUBLIC_API_KEY
      : undefined;

  return storedKey || envKey || "";
};

const axiosInstance = axios.create({
  baseURL: resolveApiBaseUrl(),
});

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError<BackendErrorResponse>(error)) {
    const payload = error.response?.data;
    return payload?.message || payload?.detail || error.message || "Request failed";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Request failed";
}

function showToast(message: string, type: "success" | "error" | "warning" | "info" = "info") {
  if (typeof window === "undefined") {
    console.error(message);
    return;
  }

  // Prefer the Arad toast system when mounted (ToastViewport registers this bridge).
  const aradToast = (window as unknown as {
    __aradToast?: (t: { type?: string; title: string }) => void;
  }).__aradToast;
  if (aradToast) {
    aradToast({ type, title: message });
    return;
  }

  const containerId = "api-client-toast-container";
  let container = document.getElementById(containerId);

  if (!container) {
    container = document.createElement("div");
    container.id = containerId;
    container.style.position = "fixed";
    container.style.top = "16px";
    container.style.right = "16px";
    container.style.zIndex = "9999";
    container.style.display = "flex";
    container.style.flexDirection = "column";
    container.style.gap = "10px";
    container.style.pointerEvents = "none";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  toast.textContent = message;
  toast.style.minWidth = "280px";
  toast.style.maxWidth = "420px";
  toast.style.padding = "12px 14px";
  toast.style.borderRadius = "12px";
  toast.style.background = "rgba(15, 23, 42, 0.96)";
  toast.style.color = "#ffffff";
  toast.style.boxShadow = "0 12px 32px rgba(0, 0, 0, 0.25)";
  toast.style.border = "1px solid rgba(255, 255, 255, 0.08)";
  toast.style.fontSize = "13px";
  toast.style.lineHeight = "1.4";
  toast.style.pointerEvents = "auto";
  toast.style.opacity = "0";
  toast.style.transform = "translateY(-8px)";
  toast.style.transition = "opacity 160ms ease, transform 160ms ease";

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  window.setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-8px)";
    window.setTimeout(() => toast.remove(), 180);
  }, 3000);
}

export { showToast };

axiosInstance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.headers = config.headers || {};
  config.headers["Content-Type"] = "application/json";
  // Base URL and API key can be changed at runtime from Settings.
  config.baseURL = resolveApiBaseUrl();
  const apiKey = resolveApiKey();
  if (apiKey) {
    config.headers["X-API-Key"] = apiKey;
  }
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    showToast(getErrorMessage(error), "error");
    return Promise.reject(error);
  }
);

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  return axiosInstance.request<T, T>(config);
}

export const apiClient = {
  get<T>(url: string, config?: AxiosRequestConfig) {
    return request<T>({ ...config, method: "GET", url });
  },
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return request<T>({ ...config, method: "POST", url, data });
  },
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return request<T>({ ...config, method: "PUT", url, data });
  },
  patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return request<T>({ ...config, method: "PATCH", url, data });
  },
  delete<T>(url: string, config?: AxiosRequestConfig) {
    return request<T>({ ...config, method: "DELETE", url });
  },
  async getFile(path: string, timeout?: number): Promise<Blob> {
    const API_URL = resolveApiBaseUrl();
    const API_KEY = resolveApiKey();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout || 30000);
    try {
      const response = await fetch(`${API_URL}${path}`, {
        method: "GET",
        signal: controller.signal,
        headers: {
          "X-API-Key": API_KEY,
        },
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw { message: `Failed to fetch ${path}`, detail: text } as ApiError;
      }
      return await response.blob();
    } finally {
      clearTimeout(timeoutId);
    }
  },
};

// ── Streaming chat (Server-Sent Events) ─────────────────────────────────────
// Each event mirrors a real operation the agent performs: a context query
// finishing (with a real row count), the reasoning step, answer tokens, and a
// final summary. The dashboard renders these directly as the live work-log.
export type AgentStreamEvent =
  | { t: "step"; id: string; phase: "start" | "done"; label?: string; detail?: string; count?: number; result?: string; status?: string }
  | { t: "delta"; text: string }
  | { t: "final"; answer: string; sources: string[]; ms: number }
  | { t: "error"; message: string };

export interface ChatStreamPayload {
  question: string;
  conversation_history: { role: string; content: string }[];
}

/**
 * POST to the streaming chat endpoint and invoke `onEvent` for each SSE frame
 * as it arrives. Resolves when the stream closes; rejects on a transport error
 * or non-2xx status (so the caller can fall back to the non-streaming endpoint).
 */
export async function streamChat(
  payload: ChatStreamPayload,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const apiKey = resolveApiKey();
  const res = await fetch(`${resolveApiBaseUrl()}/api/v1/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`chat stream failed: HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    // SSE frames are separated by a blank line.
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const json = dataLine.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as AgentStreamEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}

// GR&R
export const submitGRRAnalysis = (data: GRRInput) =>
  apiClient.post<GRRAnalysisResponse>("/api/v1/grr/analyze", data);

export const getGRRHistory = () => apiClient.get<GRRHistoryItem[]>("/api/v1/grr/history");

// SPC
export const submitSPCData = (data: SPCInput) =>
  apiClient.post<SPCDataResponse>("/api/v1/spc/data", data);

export const getSPCHistory = (processName: string) =>
  apiClient.get<SPCHistoryResponse>(`/api/v1/spc/history/${encodeURIComponent(processName)}`);

export const getSPCProcesses = () =>
  apiClient.get<SPCProcessListResponse>("/api/v1/spc/processes");

// SPC baselines (frozen control limits, Phase II monitoring)
export interface SPCBaseline {
  process_name: string;
  configured: boolean;
  ucl?: number | null;
  cl?: number | null;
  lcl?: number | null;
  sigma?: number | null;
  n_points?: number | null;
}

export interface SPCBaselineEstablishResponse {
  ok: boolean;
  reason: string;
  process_name: string;
  baseline?: SPCBaseline | null;
  violations: Record<string, number[]>;
}

export const getSPCBaseline = (processName: string) =>
  apiClient.get<SPCBaseline>(`/api/v1/spc/baseline/${encodeURIComponent(processName)}`);

export const setSPCBaseline = (
  processName: string,
  body: { measurements?: number[]; window?: number; force?: boolean } = {},
) => apiClient.post<SPCBaselineEstablishResponse>(`/api/v1/spc/baseline/${encodeURIComponent(processName)}`, body);

export const clearSPCBaseline = (processName: string) =>
  apiClient.delete<SPCBaseline>(`/api/v1/spc/baseline/${encodeURIComponent(processName)}`);

// Dashboard
export const getDashboardSummary = () =>
  apiClient.get<DashboardSummaryResponse>("/api/v1/dashboard/summary");

// Alerts
export const getAlerts = (params?: AlertFilters) =>
  apiClient.get<AlertListResponse>("/api/v1/alerts", { params });

export const resolveAlert = (id: string | number) =>
  apiClient.put<AlertResolveResponse>(`/api/v1/alerts/${id}/resolve`);

export const recordAlertFeedback = (id: string | number, data: AlertFeedbackInput) =>
  apiClient.post<AlertFeedbackResponse>(`/api/v1/alerts/${id}/feedback`, data);

export const getAlertAccuracy = () =>
  apiClient.get<AlertAccuracyResponse>("/api/v1/alerts/accuracy");

// Audit Log
export const getAuditLog = () => apiClient.get<AuditLogItem[]>("/api/v1/audit-log");

// Review Queue
export interface ReviewQueueItem {
  id: string;
  study_id: string;
  status: string;
  assigned_to?: string | null;
  due_at?: string | null;
  created_at?: string | null;
  grr_pct?: number | null;
  ndc?: number | null;
  equipment_id: string;
  characteristic_name: string;
}

export interface ReviewDecisionInput {
  decision: "approved" | "rejected";
  notes?: string;
  decided_by: string;
}

export const getReviews = () => apiClient.get<ReviewQueueItem[]>("/api/v1/reviews");

export const decideReview = (reviewId: string, data: ReviewDecisionInput) =>
  apiClient.patch<Record<string, unknown>>(`/api/v1/reviews/${reviewId}`, data);

// ── Gage registry ────────────────────────────────────────────────────────────
export interface Gage {
  id: string;
  name: string;
  type: string;
  nominal?: number | null;
  tolerance?: number | null;
  calibration_due?: string | null;
  created_at: string;
}

export interface GageInput {
  name: string;
  type?: string;
  nominal?: number | null;
  tolerance?: number | null;
  calibration_due?: string | null;
}

export const getGages = () => apiClient.get<Gage[]>("/api/v1/gages");
export const createGage = (data: GageInput) => apiClient.post<Gage>("/api/v1/gages", data);
export const deleteGage = (id: string) => apiClient.delete<void>(`/api/v1/gages/${id}`);

// ── Alert routing rules ──────────────────────────────────────────────────────
export interface AlertRuleRecord {
  id: string;
  name: string;
  trigger: string;
  threshold?: number | null;
  scope: string;
  channels: string[];
  enabled: boolean;
  created_at: string;
}

export interface AlertRuleInput {
  name: string;
  trigger: string;
  threshold?: number | null;
  scope?: string;
  channels: string[];
  enabled?: boolean;
}

export const getAlertRules = () => apiClient.get<AlertRuleRecord[]>("/api/v1/alert-rules");
export const createAlertRule = (data: AlertRuleInput) => apiClient.post<AlertRuleRecord>("/api/v1/alert-rules", data);
export const updateAlertRule = (id: string, data: Partial<AlertRuleInput>) =>
  apiClient.patch<AlertRuleRecord>(`/api/v1/alert-rules/${id}`, data);
export const deleteAlertRule = (id: string) => apiClient.delete<void>(`/api/v1/alert-rules/${id}`);

// ── System settings (admin: integration credentials + LLM key) ────────────────
export interface SettingItem {
  key: string;
  secret: boolean;
  configured: boolean;
  value?: string;
}

export interface IntegrationTest {
  ok: boolean;
  message: string;
  ts?: number;
}

export const getSettings = () =>
  apiClient.get<{ settings: SettingItem[]; tests?: Record<string, IntegrationTest> }>("/api/v1/settings");
export const updateSettings = (values: Record<string, string>) =>
  apiClient.put<{ settings: SettingItem[] }>("/api/v1/settings", { values });
export const testIntegration = (channel: string) =>
  apiClient.post<{ ok: boolean; message: string }>("/api/v1/settings/test", { channel });
export const clearIntegration = (channel: string) =>
  apiClient.delete<{ settings: SettingItem[] }>(`/api/v1/settings/${channel}`);

// ── Bulk measurement upload (CSV / Excel) ─────────────────────────────────────
export interface UploadResult {
  received: number;
  ingested: number;
  duplicates?: number;
  skipped: number;
  mapping?: Record<string, string>;
  columns?: string[];
}

export async function uploadMeasurements(
  file: File,
  mapping?: Record<string, string>,
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  if (mapping && Object.keys(mapping).length > 0) {
    form.append("mapping", JSON.stringify(mapping));
  }
  const apiKey = resolveApiKey();
  // Do NOT set Content-Type — the browser adds the multipart boundary itself.
  const res = await fetch(`${resolveApiBaseUrl()}/api/v1/measurements/upload`, {
    method: "POST",
    headers: apiKey ? { "X-API-Key": apiKey } : {},
    body: form,
  });
  if (!res.ok) {
    let detail = `Upload failed (HTTP ${res.status})`;
    try {
      const payload = await res.json();
      detail = payload.detail || payload.message || detail;
    } catch {
      /* keep default message */
    }
    throw new Error(detail);
  }
  return (await res.json()) as UploadResult;
}

export function useApi<T>(apiCall: () => Promise<T>, deps: unknown[] = []): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    let active = true;

    async function run() {
      setLoading(true);
      setError(null);

      try {
        const result = await apiCall();
        if (active) {
          setData(result);
        }
      } catch (err) {
        if (active) {
          setError(getErrorMessage(err));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    run();

    return () => {
      active = false;
    };
  }, [apiCall, refreshIndex, ...deps]);

  return {
    data,
    loading,
    error,
    refetch: () => setRefreshIndex((value) => value + 1),
  };
}
