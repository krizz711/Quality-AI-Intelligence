/**
 * Type Definitions from Backend API
 * Auto-generated from Pydantic schemas in api/main.py and api/ai_routes.py
 */

// ─── GR&R Study Types ───────────────────────────────────────────────────────

export interface GRRStudyRequest {
  part_ids: string[];
  operator_ids: string[];
  measurements: Array<{
    part: string;
    operator: string;
    value: number;
  }>;
  method: 'xbar_r' | 'anova';
  tolerance?: number;
  equipment_id?: string;
  metadata?: Record<string, unknown>;
}

export interface GRRStudyResponse {
  study_id: string;
  grr_percent: number;
  acceptance: 'acceptable' | 'conditional' | 'not_acceptable';
  ndc: number;
  details?: Record<string, unknown>;
}

export interface GRRDetails {
  equipment_id: string;
  characteristic_name: string;
  ev: number; // Equipment Variation (Repeatability)
  av: number; // Appraiser Variation (Reproducibility)
  pv: number; // Part Variation
  status: string;
}

export interface GRRNarrativeResponse {
  study_id: string;
  equipment_id: string;
  characteristic_name: string;
  grr_percent: number;
  acceptance: string;
  narrative: {
    summary: string;
    root_cause_analysis: string;
    recommendations: string[];
    risk_assessment: string;
    confidence: number;
  };
}

// ─── SPC Types ──────────────────────────────────────────────────────────────

export interface SPCRequest {
  values: number[];
  chart_type: 'xbar_r' | 'i_mr' | 'p';
  subgroup_size?: number;
  part_number?: string;
  characteristic_name?: string;
}

export interface SPCResponse {
  chart_type: string;
  ucl: number;
  cl: number;
  lcl: number;
  out_of_control_indices: number[];
  nelson_violations: Record<string, number[]>;
}

export interface SPCInterpretRequest {
  chart_type: string;
  part_number?: string;
  characteristic_name?: string;
  violated_rules: Record<string, number[]>;
  ucl: number;
  cl: number;
  lcl: number;
  recent_values: number[];
}

export interface SPCInterpretResponse {
  pattern_description: string;
  manufacturing_significance: string;
  likely_causes: string[];
  urgency: string;
  recommended_actions: string[];
}

export interface PredictRequest {
  part_number: string;
  characteristic_name: string;
  values_history: number[];
  ucl: number;
  cl: number;
  lcl: number;
  recent_grr_pct?: number;
}

export interface PredictResponse {
  trend_summary: string;
  predicted_violation_risk: string;
  time_to_action: string;
  leading_indicators: string[];
  preventive_actions: string[];
}

// ─── Review Queue Types ─────────────────────────────────────────────────────

export interface ReviewQueueResponse {
  id: string; // UUID
  study_id: string; // UUID
  status: 'pending' | 'approved' | 'rejected';
  assigned_to?: string;
  due_at?: string; // ISO datetime
  created_at?: string; // ISO datetime
  grr_pct?: number;
  ndc?: number;
  equipment_id: string;
  characteristic_name: string;
}

export interface ReviewDecision {
  decision: 'approved' | 'rejected';
  notes?: string;
  decided_by: string;
}

export interface ReviewDecisionResponse {
  review_id: string;
  study_id: string;
  decision: string;
  decided_by: string;
  message: string;
}

// ─── Chat Types ─────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  question: string;
  conversation_history?: ChatMessage[];
  context_override?: Record<string, unknown>;
}

export interface ChatResponse {
  answer: string;
  context_used: string[];
}

// ─── Health Check ───────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'down';
  version: string;
}

// ─── UI Domain Models (transformed from backend responses) ───────────────────

/**
 * GRRStudy as displayed in the UI
 * Combines fields from GRRStudyResponse + ReviewQueueResponse
 */
export interface UIGRRStudy {
  id: string;
  equipment_id: string;
  characteristic_name: string;
  grr_pct: number;
  ndc: number;
  acceptance: 'acceptable' | 'conditional' | 'not_acceptable';
  ev?: number;
  av?: number;
  pv?: number;
  status?: string;
  created_at?: Date;
  ai_narrative?: string;
  // Review queue fields (if applicable)
  review_id?: string;
  review_status?: 'pending' | 'approved' | 'rejected';
}

/**
 * SPCChart as displayed in the UI
 * Combines fields from SPCResponse + historical data
 */
export interface UISPCChart {
  id: string;
  machine_id: string;
  part_number: string;
  characteristic: string;
  chart_type: 'xbar_r' | 'i_mr' | 'p';
  ucl: number;
  cl: number;
  lcl: number;
  data: Array<{
    index: number;
    value: number;
    violation?: string;
  }>;
  active_violations: Array<{
    rule: string;
    points: number[];
    severity: 'critical' | 'warning';
  }>;
  status: 'stable' | 'warning' | 'critical';
  interpretation?: SPCInterpretResponse;
  prediction?: PredictResponse;
}

// ─── Type Guards ────────────────────────────────────────────────────────────

export function isGRRAcceptable(
  acceptance: string
): acceptance is 'acceptable' | 'conditional' | 'not_acceptable' {
  return ['acceptable', 'conditional', 'not_acceptable'].includes(acceptance);
}

export function isSPCStatus(status: string): status is 'stable' | 'warning' | 'critical' {
  return ['stable', 'warning', 'critical'].includes(status);
}

export function isChartType(type: string): type is 'xbar_r' | 'i_mr' | 'p' {
  return ['xbar_r', 'i_mr', 'p'].includes(type);
}
