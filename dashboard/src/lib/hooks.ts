/**
 * Custom React Hooks for Data Fetching
 * Manages loading, error, and caching state for API calls
 */

import { useEffect, useState, useCallback } from 'react';
import { apiClient, type ApiError } from '@/api/apiClient';
import type {
  UIGRRStudy,
  UISPCChart,
  GRRStudyResponse,
  ReviewQueueResponse,
  SPCResponse,
  SPCInterpretResponse,
  PredictResponse,
} from './types';

export interface UseAsyncState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | Error | null;
  retry: () => void;
}

/**
 * Generic hook for async data fetching with caching & error handling
 */
export function useAsync<T>(
  asyncFn: () => Promise<T>,
  deps: unknown[] = []
): UseAsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | Error | null>(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await asyncFn();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    execute();
  }, [execute]);

  return { data, loading, error, retry: execute };
}

// ─── GR&R Hooks ─────────────────────────────────────────────────────────────

/**
 * Fetch pending GR&R reviews from the backend
 */
export function useGRRReviews(): UseAsyncState<UIGRRStudy[]> {
  return useAsync(async () => {
    const reviews = await apiClient.get<ReviewQueueResponse[]>('/api/v1/reviews');
    return reviews.map(transformReviewToUIGRRStudy);
  });
}

/**
 * Fetch a single GR&R study by ID
 */
export function useGRRStudy(
  studyId: string | null
): UseAsyncState<UIGRRStudy | null> {
  return useAsync(
    async () => {
      if (!studyId) return null;
      const response = await apiClient.get<GRRStudyResponse>(`/api/v1/studies/${studyId}`);
      return transformStudyResponseToUI(studyId, response);
    },
    [studyId]
  );
}

/**
 * Fetch AI narrative for a study
 */
export function useGRRNarrative(studyId: string | null) {
  return useAsync(
    async () => {
      if (!studyId) return null;
      const response = await apiClient.post(`/api/v1/studies/${studyId}/narrative`);
      return response;
    },
    [studyId]
  );
}

/**
 * Download GR&R PDF report
 */
export async function downloadGRRReport(studyId: string) {
  const blob = await apiClient.getFile(`/api/v1/studies/${studyId}/report`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `grr_report_${studyId.slice(0, 8)}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─── SPC Hooks ──────────────────────────────────────────────────────────────

/**
 * Analyze SPC data and get control chart
 */
export async function analyzeSPC(values: number[], chartType: string = 'xbar_r') {
  return apiClient.post<SPCResponse>('/api/v1/spc/analyze', {
    values,
    chart_type: chartType,
    subgroup_size: 5,
  });
}

/**
 * Get AI interpretation of SPC violations
 */
export async function interpretSPCViolations(
  chartType: string,
  violatedRules: Record<string, number[]>,
  ucl: number,
  cl: number,
  lcl: number,
  recentValues: number[]
) {
  return apiClient.post<SPCInterpretResponse>('/api/v1/spc/interpret', {
    chart_type: chartType,
    violated_rules: violatedRules,
    ucl,
    cl,
    lcl,
    recent_values: recentValues,
  });
}

/**
 * Get predictive violation risk
 */
export async function predictSPCViolations(
  partNumber: string,
  characteristicName: string,
  valuesHistory: number[],
  ucl: number,
  cl: number,
  lcl: number,
  recentGrrPct?: number
) {
  return apiClient.post<PredictResponse>('/api/v1/spc/predict', {
    part_number: partNumber,
    characteristic_name: characteristicName,
    values_history: valuesHistory,
    ucl,
    cl,
    lcl,
    recent_grr_pct: recentGrrPct,
  });
}

// ─── Review Queue Hooks ─────────────────────────────────────────────────────

/**
 * Approve or reject a pending review
 */
export async function submitReviewDecision(
  reviewId: string,
  decision: 'approved' | 'rejected',
  notes: string = '',
  decidedBy: string = 'quality-engineer'
) {
  return apiClient.patch(`/api/v1/reviews/${reviewId}`, {
    decision,
    notes,
    decided_by: decidedBy,
  });
}

// ─── Chat Hook ──────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export async function chatWithAgent(
  question: string,
  conversationHistory: ChatMessage[] = []
) {
  return apiClient.post('/api/v1/chat', {
    question,
    conversation_history: conversationHistory,
  });
}

// ─── Transformers ───────────────────────────────────────────────────────────

/**
 * Transform backend GRRStudyResponse to UI domain model
 */
function transformStudyResponseToUI(
  studyId: string,
  response: GRRStudyResponse
): UIGRRStudy {
  const details = (response.details || {}) as Record<string, unknown>;
  return {
    id: studyId,
    equipment_id: (details.equipment_id as string) || 'UNKNOWN',
    characteristic_name: (details.characteristic_name as string) || 'UNKNOWN',
    grr_pct: response.grr_percent,
    ndc: response.ndc,
    acceptance: response.acceptance,
    ev: (details.ev as number) || 0,
    av: (details.av as number) || 0,
    pv: (details.pv as number) || 0,
    status: (details.status as string) || response.acceptance,
  };
}

/**
 * Transform ReviewQueueResponse to UI domain model
 */
function transformReviewToUIGRRStudy(review: ReviewQueueResponse): UIGRRStudy {
  return {
    id: review.study_id,
    review_id: review.id,
    equipment_id: review.equipment_id,
    characteristic_name: review.characteristic_name,
    grr_pct: review.grr_pct || 0,
    ndc: review.ndc || 0,
    acceptance: 'conditional', // Reviews are typically CONDITIONAL studies
    review_status: review.status,
    created_at: review.created_at ? new Date(review.created_at) : undefined,
  };
}

/**
 * Transform SPCResponse to UI domain model
 */
export function transformSPCResponseToUI(
  response: SPCResponse,
  machineId: string,
  partNumber: string = 'UNKNOWN',
  characteristicName: string = 'UNKNOWN'
): UISPCChart {
  // Map Nelson violations to UI violations array
  const activeViolations: UISPCChart['active_violations'] = [];
  for (const [rule, indices] of Object.entries(response.nelson_violations || {})) {
    if (indices.length > 0) {
      activeViolations.push({
        rule,
        points: indices,
        severity: rule === 'rule_1' ? 'critical' : 'warning',
      });
    }
  }

  // Determine status based on violations
  let status: 'stable' | 'warning' | 'critical' = 'stable';
  if (activeViolations.some((v) => v.severity === 'critical')) {
    status = 'critical';
  } else if (activeViolations.length > 0) {
    status = 'warning';
  }

  return {
    id: `spc_${machineId}_${Date.now()}`,
    machine_id: machineId,
    part_number: partNumber,
    characteristic: characteristicName,
    chart_type: (response.chart_type as any) || 'xbar_r',
    ucl: response.ucl,
    cl: response.cl,
    lcl: response.lcl,
    data: response.out_of_control_indices.map((idx) => ({
      index: idx,
      value: 0, // Would need actual data points from request
      violation: 'out_of_control',
    })),
    active_violations: activeViolations,
    status,
  };
}
