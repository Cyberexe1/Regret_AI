/**
 * TypeScript types for the REGRET ENGINE FastAPI backend contract.
 *
 * Mirrors the backend's actual Pydantic schemas field-for-field (read
 * directly from app/schemas/*.py and app/agents/orchestrator.py, not
 * guessed) - see backend/README.md for the authoritative source. These are
 * the *wire* types: what the API actually sends/accepts. UI-facing
 * presentational types (`@/types`) are intentionally separate and derived
 * from these where a page needs to combine or reshape API data for display.
 *
 * Naming: snake_case is kept as-is (matching the JSON the backend actually
 * returns) rather than converted to camelCase, so there is never a
 * translation step that could silently drop or rename a field the backend
 * added.
 */

/* -------------------------------------------------------------------------- *
 * Shared enums (exact string values from app/schemas/decision_resources.py
 * and app/schemas/decision.py)
 * -------------------------------------------------------------------------- */

export type DecisionStatus =
  | 'draft'
  | 'queued'
  | 'analyzing'
  | 'completed'
  | 'needs_validation'
  | 'archived';

export type AnalysisRunStatus = 'queued' | 'running' | 'completed' | 'failed';

export type AgentRunStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'unavailable';

/** The 9 pipeline stage ids used as `stage_statuses` keys, in pipeline order. */
export const ANALYSIS_STAGE_IDS = [
  'decision_analyzer',
  'assumption_hunter',
  'blindspot_hunter',
  'research_agent',
  'evidence_agent',
  'devils_advocate',
  'regret_simulator',
  'threshold_engine',
  'experiment_planner',
] as const;

export type AnalysisStageId = (typeof ANALYSIS_STAGE_IDS)[number];

export type SourceType = 'document' | 'url' | 'note';

export type EvidenceStatus = 'unverified' | 'supported' | 'contradicted' | 'not_addressed';

export type BlindspotEvidenceStatus =
  | 'unknown'
  | 'already_supported'
  | 'partially_addressed'
  | 'contradicted'
  | 'not_addressed';

export type AssumptionSourceKind = 'explicit' | 'implicit';

export type ExperimentStatus = 'recommended' | 'planned' | 'active' | 'completed' | 'cancelled';

export type ExperimentOutcome = 'success' | 'failure' | 'inconclusive' | 'partial';

export type ThresholdComparisonStatus =
  | 'above'
  | 'below'
  | 'within_range'
  | 'outside_range'
  | 'met'
  | 'missed'
  | 'inconclusive'
  | 'unknown';

export type AssumptionReevaluationStatus =
  | 'supported'
  | 'partially_supported'
  | 'contradicted'
  | 'still_uncertain'
  | 'insufficient_evidence';

export type RegretScenarioReevaluationStatus =
  | 'plausible'
  | 'evidence_strengthened'
  | 'evidence_weakened'
  | 'still_uncertain';

export type DecisionAssessmentStatus =
  | 'strengthened'
  | 'weakened'
  | 'unchanged'
  | 'inconclusive'
  | 'requires_more_evidence';

/* -------------------------------------------------------------------------- *
 * Decisions (app/schemas/decision.py)
 * -------------------------------------------------------------------------- */

export interface ApiDecisionCreate {
  title: string;
  description: string;
  desired_outcome?: string | null;
  budget?: number | null;
  currency?: string | null;
  timeline?: string | null;
  location?: string | null;
  risk_tolerance?: string | null;
  beliefs?: string | null;
}

export interface ApiDecisionUpdate {
  title?: string | null;
  description?: string | null;
  desired_outcome?: string | null;
  budget?: number | null;
  currency?: string | null;
  timeline?: string | null;
  location?: string | null;
  risk_tolerance?: string | null;
  beliefs?: string | null;
  status?: DecisionStatus | null;
  expected_updated_at?: string | null;
}

export interface ApiDecision {
  id: string;
  title: string;
  description: string;
  desired_outcome: string | null;
  budget: number | null;
  currency: string | null;
  timeline: string | null;
  location: string | null;
  risk_tolerance: string | null;
  beliefs: string | null;
  status: DecisionStatus;
  created_at: string;
  updated_at: string;
}

export interface ApiDecisionListResponse {
  items: ApiDecision[];
  next_cursor: string | null;
}

/* -------------------------------------------------------------------------- *
 * Evidence (app/schemas/decision_resources.py::Evidence)
 * -------------------------------------------------------------------------- */

export interface ApiEvidence {
  id: string;
  decision_id: string;
  title: string;
  source_type: SourceType;
  source_url: string | null;
  storage_key: string | null;
  filename: string | null;
  file_type: string | null;
  size_bytes: number | null;
  page_count: number | null;
  content_reference: string | null;
  content_truncated: boolean;
  credibility: string | null;
  created_at: string;
}

/* -------------------------------------------------------------------------- *
 * Analysis (app/schemas/analysis.py)
 * -------------------------------------------------------------------------- */

export interface ApiAnalysisRunResponse {
  analysis_run_id: string;
  decision_id: string;
  status: AnalysisRunStatus;
}

export interface ApiAnalysisRunStatusResponse {
  analysis_run_id: string;
  decision_id: string;
  status: AnalysisRunStatus;
  current_stage: AnalysisStageId | null;
  stage_statuses: Partial<Record<AnalysisStageId, AgentRunStatus>>;
  created_at: string | null;
  updated_at: string | null;
  error_message: string | null;
}

/* -------------------------------------------------------------------------- *
 * Assumptions / Blindspots / Evidence findings / Challenges / Regret
 * scenarios / Thresholds / Re-evaluations
 * (app/schemas/decision_resources.py - read-only via
 * app/api/routes/decision_analysis_resources.py)
 * -------------------------------------------------------------------------- */

export interface ApiAssumption {
  id: string;
  decision_id: string;
  statement: string;
  source: AssumptionSourceKind | null;
  importance: string | null;
  confidence: number | null;
  evidence_status: EvidenceStatus;
  dependency: string | null;
  failure_consequence: string | null;
  reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiBlindspot {
  id: string;
  decision_id: string;
  question: string;
  category: string | null;
  importance: string | null;
  confidence: number | null;
  evidence_status: BlindspotEvidenceStatus;
  related_assumption_ids: string[];
  why_it_matters: string | null;
  evidence_gap: string | null;
  reason: string | null;
  created_at: string;
}

export interface ApiEvidenceFinding {
  id: string;
  decision_id: string;
  evidence_id: string;
  claim: string;
  support_level: string | null;
  credibility: string | null;
  related_assumption_ids: string[];
  related_blindspot_ids: string[];
  explanation: string | null;
  excerpt: string | null;
  created_at: string;
}

export interface ApiChallenge {
  id: string;
  decision_id: string;
  claim: string;
  attack: string;
  severity: string | null;
  confidence: number | null;
  related_assumption_ids: string[];
  related_blindspot_ids: string[];
  related_evidence_finding_ids: string[];
  failure_mechanism: string | null;
  evidence_basis: string | null;
  created_at: string;
}

export interface ApiRegretScenario {
  id: string;
  decision_id: string;
  title: string;
  failure_condition: string;
  probability_band: string | null;
  impact: string | null;
  regret_level: string | null;
  trigger_variable: string | null;
  trigger_direction: string | null;
  provisional_threshold: string | null;
  consequence: string | null;
  related_assumption_ids: string[];
  related_challenge_ids: string[];
  evidence_basis: string | null;
  created_at: string;
}

export interface ApiThreshold {
  id: string;
  decision_id: string;
  variable: string;
  threshold_type: string | null;
  direction: string | null;
  threshold_value: string | null;
  lower_bound: number | null;
  upper_bound: number | null;
  unit: string | null;
  confidence: number | null;
  derivation: string | null;
  consequence: string | null;
  related_regret_scenario_ids: string[];
  related_assumption_ids: string[];
  evidence_basis: string | null;
  validation_status: string | null;
  calculation_formula: string | null;
  calculation_inputs: Record<string, number> | null;
  calculation_provenance: string | null;
  created_at: string;
}

export interface ApiExternalEvidence {
  id: string;
  decision_id: string;
  research_result_id: string;
  claim: string;
  source_url: string;
  source_name: string;
  support_level: string | null;
  credibility: string | null;
  related_assumption_ids: string[];
  related_blindspot_ids: string[];
  related_threshold_ids: string[];
  explanation: string | null;
  excerpt: string | null;
  published_at: string | null;
  retrieved_at: string;
  created_at: string;
}

/* -------------------------------------------------------------------------- *
 * Experiments (app/schemas/decision_resources.py::Experiment/ExperimentResult)
 * -------------------------------------------------------------------------- */

export interface ApiExperiment {
  id: string;
  decision_id: string;
  title: string;
  objective: string | null;
  hypothesis: string;
  target_threshold_id: string | null;
  variable_to_test: string | null;
  experiment_type: string | null;
  steps: string[];
  success_criteria: string[];
  failure_criteria: string[];
  duration_days: number | null;
  estimated_cost: number | null;
  currency: string | null;
  evidence_to_collect: string[];
  decision_rule: string | null;
  expected_information_gain: string | null;
  confidence: number | null;
  feasibility: string | null;
  reversibility: string | null;
  related_assumption_ids: string[];
  related_regret_scenario_ids: string[];
  status: ExperimentStatus;
  created_at: string;
  updated_at: string;
}

export interface ApiExperimentResult {
  id: string;
  decision_id: string;
  experiment_id: string;
  outcome: ExperimentOutcome;
  summary: string;
  observations: string[];
  measured_values: Record<string, string | number | boolean>;
  evidence_ids: string[];
  notes: string | null;
  completed_at: string;
}

export interface ApiExperimentResultCreate {
  outcome: ExperimentOutcome;
  summary: string;
  observations?: string[];
  measured_values?: Record<string, string | number | boolean>;
  evidence_ids?: string[];
  notes?: string | null;
  completed_at?: string | null;
}

export interface ApiExperimentResultResponse {
  experiment_id: string;
  result_id: string;
  reevaluation_id: string;
  status: AnalysisRunStatus;
  decision_assessment: DecisionAssessmentStatus;
  key_learning: string;
  next_step: string;
}

/* -------------------------------------------------------------------------- *
 * Re-evaluation (app/schemas/decision_resources.py::ReEvaluation)
 * -------------------------------------------------------------------------- */

export interface ApiThresholdComparison {
  threshold_id: string;
  variable: string;
  observed_value: string | null;
  threshold_value: string | null;
  status: ThresholdComparisonStatus;
  explanation: string;
}

export interface ApiAssumptionReevaluation {
  assumption_id: string;
  previous_status: string | null;
  new_status: AssumptionReevaluationStatus;
  explanation: string;
}

export interface ApiRegretScenarioReevaluation {
  regret_scenario_id: string;
  previous_status: string | null;
  new_status: RegretScenarioReevaluationStatus;
  explanation: string;
}

export interface ApiDecisionAssessment {
  status: DecisionAssessmentStatus;
  confidence: number;
  summary: string;
  changed_assumptions: string[];
  affected_thresholds: string[];
  affected_regret_scenarios: string[];
  recommended_next_step: string;
  evidence_basis: string[];
}

export interface ApiReEvaluation {
  id: string;
  decision_id: string;
  experiment_id: string;
  experiment_result_id: string;
  previous_assessment: string;
  new_assessment: string;
  threshold_comparisons: ApiThresholdComparison[];
  assumption_reevaluations: ApiAssumptionReevaluation[];
  regret_scenario_reevaluations: ApiRegretScenarioReevaluation[];
  decision_assessment: ApiDecisionAssessment;
  changed_thresholds: string[];
  changed_assumptions: string[];
  changed_regret_scenarios: string[];
  key_learning: string;
  recommended_next_step: string;
  created_at: string;
}

/* -------------------------------------------------------------------------- *
 * Health (app/schemas/health.py)
 * -------------------------------------------------------------------------- */

export interface ApiDependencyStatus {
  name: string;
  status: 'ok' | 'unavailable' | 'not_configured';
  required: boolean;
}

export interface ApiHealthResponse {
  status: string;
  service: string;
}

export interface ApiReadinessResponse {
  status: 'ready' | 'degraded';
  dependencies: ApiDependencyStatus[];
}

/* -------------------------------------------------------------------------- *
 * Standardized error envelope (app/core/errors.py)
 * -------------------------------------------------------------------------- */

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id: string | null;
  };
  detail: string;
}
