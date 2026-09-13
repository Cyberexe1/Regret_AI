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
 * Decision Memory (REGRET ENGINE 2.0, backend/app/memory/memory_schemas.py)
 * -------------------------------------------------------------------------- */

export type MemoryStage = 'preliminary' | 'validated';

export type LearningType =
  | 'assumption_validated'
  | 'assumption_weakened'
  | 'assumption_failed'
  | 'threshold_validated'
  | 'threshold_failed'
  | 'threshold_inconclusive'
  | 'unexpected_result'
  | 'experiment_learning'
  | 'decision_outcome'
  | 'unresolved_uncertainty';

export type LearningSourceType =
  | 'experiment_result'
  | 're_evaluation'
  | 'evidence'
  | 'decision'
  | 'analysis';

export interface ApiMemoryLearning {
  learning_id: string;
  memory_id: string;
  decision_id: string;
  statement: string;
  learning_type: LearningType;
  source_type: LearningSourceType;
  source_id: string;
  confidence: number | null;
  evidence_basis: string[];
  observed_value: string | null;
  expected_value: string | null;
  variance_description: string | null;
  related_assumption_ids: string[];
  related_threshold_ids: string[];
  related_regret_scenario_ids: string[];
  created_at: string;
}

export interface ApiDecisionMemory {
  memory_id: string;
  decision_id: string;
  user_id: string;
  decision_type: string | null;
  decision_summary: string;
  created_at: string;
  completed_at: string | null;
  stage: MemoryStage;
  original_assessment: string | null;
  critical_assumption_ids: string[];
  critical_threshold_ids: string[];
  critical_regret_scenario_ids: string[];
  experiment_ids: string[];
  outcome_summary: string | null;
  validated_learnings: string[];
  unresolved_uncertainties: string[];
  final_assessment: string | null;
  confidence: number | null;
  tags: string[];
  source_analysis_run_id: string | null;
  updated_at: string;
}

export interface ApiDecisionMemoryResponse {
  memory: ApiDecisionMemory | null;
  learnings: ApiMemoryLearning[];
  experiments: ApiExperiment[];
  assessments: ApiReEvaluation[];
  unresolved_uncertainties: string[];
}

/* -------------------------------------------------------------------------- *
 * Decision Similarity & Historical Insight Engine (REGRET ENGINE 2.0,
 * backend/app/memory/similarity_schemas.py)
 * -------------------------------------------------------------------------- */

export interface ApiSimilarityScore {
  decision_id: string;
  /** Deterministic, explainable similarity score in [0, 1] - NOT a
   * probability or a statistically calibrated measure of anything. */
  score: number;
  matched_features: string[];
  explanation: string;
  confidence: number;
}

export interface ApiHistoricalInsight {
  insight_id: string;
  source_decision_id: string;
  source_memory_id: string;
  learning_id: string;
  /** Copied verbatim from the source MemoryLearning. */
  statement: string;
  /** Historical relevance score - how similar the source decision was.
   * NOT a probability that this insight applies to the current decision. */
  relevance_score: number;
  relevance_reason: string;
  learning_type: LearningType;
  source_type: LearningSourceType;
  observed_value: string | null;
  expected_value: string | null;
  related_variable: string | null;
  confidence: number | null;
  created_at: string;
}

export interface ApiHistoricalContext {
  found: boolean;
  relevant_decisions: ApiSimilarityScore[];
  relevant_decisions_count: number;
  relevant_learnings: ApiHistoricalInsight[];
  recurring_variables: string[];
  previously_failed_assumptions: string[];
  previously_validated_thresholds: string[];
  unresolved_patterns: string[];
  warnings: string[];
}

/* -------------------------------------------------------------------------- *
 * Value of Information (REGRET ENGINE 2.0, Step 20,
 * backend/app/agents/value_of_information_schemas.py)
 * -------------------------------------------------------------------------- */

export type DecisionSensitivity = 'negligible' | 'low' | 'moderate' | 'high' | 'critical' | 'unknown';

export type UncertaintyLevel = 'low' | 'medium' | 'high' | 'very_high' | 'unknown';

export type EvidenceStrength = 'none' | 'weak' | 'moderate' | 'strong' | 'unknown';

export type CostBand = 'low' | 'medium' | 'high' | 'unknown';

export type HistoricalRelevance = 'none' | 'low' | 'medium' | 'high';

/** Deliberately five qualitative levels (plus 'unknown') - never a raw
 * float presented as a calibrated probability. See the backend's own
 * `ValueBand` docstring. */
export type ValueBand = 'very_low' | 'low' | 'medium' | 'high' | 'very_high' | 'unknown';

export type ThresholdLinkStatus = 'linked' | 'not_established';

/** REGRET ENGINE 2.0, Step 23 - see backend/app/learning/schemas.py. */
export type HistoricalLearningSignal = 'none' | 'weak' | 'moderate' | 'strong';

export interface ApiValueOfInformationItem {
  uncertainty_id: string;
  title: string;
  description: string;
  related_assumption_ids: string[];
  related_blindspot_ids: string[];
  related_threshold_ids: string[];
  related_regret_scenario_ids: string[];
  related_experiment_id: string | null;
  potential_decision_impact: string | null;
  decision_sensitivity: DecisionSensitivity;
  regret_severity: string | null;
  current_evidence_strength: EvidenceStrength;
  uncertainty_level: UncertaintyLevel;
  estimated_test_cost: CostBand;
  estimated_test_duration_days: number | null;
  feasibility: string | null;
  reversibility: string | null;
  historical_relevance: HistoricalRelevance;
  prior_learning_count: number;
  /** REGRET ENGINE 2.0, Step 23: how strongly a recurring Cross-Decision
   * Pattern bears on this uncertainty's variable - a tiebreaker-strength
   * signal only, never something that overrides current evidence. */
  historical_learning_signal: HistoricalLearningSignal;
  historical_learning_explanation: string | null;
  threshold_status: ThresholdLinkStatus;
  information_value: ValueBand;
  practical_value: ValueBand;
  priority: number;
  rationale: string;
  /** How much of this score rests on real, comparable inputs - NEVER a
   * probability that the uncertainty will resolve favorably. */
  confidence: number;
}

export interface ApiValueOfInformationAnalysis {
  analysis_id: string;
  decision_id: string;
  ranked_uncertainties: ApiValueOfInformationItem[];
  primary_uncertainty_id: string | null;
  primary_threshold_id: string | null;
  why_this_is_primary: string | null;
  summary: string;
  methodology_version: string;
  created_at: string;
  superseded_by_analysis_id: string | null;
}

/* -------------------------------------------------------------------------- *
 * Adaptive Experiment Loop (REGRET ENGINE 2.0, Step 21,
 * backend/app/adaptive/schemas.py)
 * -------------------------------------------------------------------------- */

export type AdaptiveCycleStatus =
  | 'awaiting_experiment'
  | 'experiment_active'
  | 'awaiting_result'
  | 're_evaluating'
  | 'selecting_next_test'
  | 'ready_for_next_experiment'
  | 'sufficiently_validated'
  | 'inconclusive'
  | 'user_stopped'
  | 'blocked';

/** The decision's current evidence-supported state - NEVER a probability
 * and NEVER a verdict on whether the decision is "correct." See the
 * backend's own `DecisionValidationState` docstring. */
export type DecisionValidationState =
  | 'strongly_supported'
  | 'supported'
  | 'partially_supported'
  | 'insufficient_evidence'
  | 'weakened'
  | 'strongly_weakened'
  | 'inconclusive'
  | 'requires_more_testing';

export type ThresholdState = 'unknown' | 'provisional' | 'under_test' | 'validated' | 'failed' | 'inconclusive';

export interface ApiThresholdCycleRecord {
  threshold_id: string;
  previous_status: ThresholdState;
  current_status: ThresholdState;
  observed_value: string | null;
  required_value: string | null;
  confidence: number | null;
  validation_status: string | null;
}

export interface ApiAdaptiveExperimentState {
  state_id: string;
  decision_id: string;
  user_id: string;
  cycle_number: number;
  current_status: AdaptiveCycleStatus;
  current_primary_uncertainty_id: string | null;
  current_primary_threshold_id: string | null;
  current_experiment_id: string | null;
  previous_experiment_id: string | null;
  previous_result_id: string | null;
  previous_assessment: DecisionValidationState | null;
  current_assessment: DecisionValidationState;
  uncertainty_status: ApiThresholdCycleRecord[];
  stopping_reason: string | null;
  next_action: string;
  why_this_is_next: string | null;
  created_at: string;
  updated_at: string;
}

export type AdvanceOutcome =
  | 'started_first_cycle'
  | 'advanced_to_next_experiment'
  | 'concluded'
  | 'no_change';

export interface ApiAdaptiveAdvanceResponse {
  state: ApiAdaptiveExperimentState;
  outcome: AdvanceOutcome;
}

/* -------------------------------------------------------------------------- *
 * Decision Evolution & Causal Timeline (REGRET ENGINE 2.0, Step 22,
 * backend/app/evolution/schemas.py)
 * -------------------------------------------------------------------------- */

export type EvolutionEventType =
  | 'decision_created'
  | 'analysis_completed'
  | 'assumption_identified'
  | 'blindspot_identified'
  | 'regret_scenario_identified'
  | 'threshold_identified'
  | 'experiment_recommended'
  | 'experiment_started'
  | 'experiment_completed'
  | 'experiment_result'
  | 'threshold_validated'
  | 'threshold_failed'
  | 're_evaluation'
  | 'assessment_changed'
  | 'learning_recorded'
  | 'next_experiment_selected'
  | 'validation_state_changed'
  | 'decision_completed'
  | 'historical_insight_surfaced';

/** How much this event mattered to the decision's overall evolution -
 * used only to decide what counts as a "major change", never a severity
 * score presented as a statistic. */
export type EvolutionImpact = 'minor' | 'moderate' | 'major';

export interface ApiDecisionEvolutionEvent {
  event_id: string;
  decision_id: string;
  cycle_number: number | null;
  event_type: EvolutionEventType;
  timestamp: string;
  title: string;
  summary: string;
  source_type: string;
  source_id: string;
  impact: EvolutionImpact;
  previous_state: string | null;
  new_state: string | null;
  reason: string | null;
  affected_assumption_ids: string[];
  affected_threshold_ids: string[];
  affected_experiment_ids: string[];
  affected_regret_scenario_ids: string[];
  evidence_ids: string[];
  is_historical: boolean;
}

export interface ApiDecisionDelta {
  changed: boolean;
  assessment_changed: boolean;
  assumptions_changed: string[];
  thresholds_changed: string[];
  uncertainties_changed: string[];
  experiments_changed: string[];
  learnings_added: string[];
  explanation: string;
}

export interface ApiDecisionEvolution {
  decision_id: string;
  user_id: string;
  current_assessment: string;
  current_cycle: number | null;
  total_cycles: number;
  timeline: ApiDecisionEvolutionEvent[];
  major_changes: ApiDecisionEvolutionEvent[];
  current_uncertainties: string[];
  validated_thresholds: string[];
  failed_thresholds: string[];
  current_primary_uncertainty: string | null;
  truncated: boolean;
  generated_at: string;
}

/* -------------------------------------------------------------------------- *
 * Cross-Decision Learning Engine (REGRET ENGINE 2.0, Step 23,
 * backend/app/learning/schemas.py)
 * -------------------------------------------------------------------------- */

export type PatternType =
  | 'recurring_failed_assumption'
  | 'recurring_validated_assumption'
  | 'recurring_threshold_failure'
  | 'recurring_threshold_validation'
  | 'recurring_uncertainty'
  | 'recurring_experiment_learning'
  | 'recurring_experiment_success'
  | 'recurring_experiment_failure'
  | 'recurring_unresolved_question'
  | 'recurring_unexpected_result';

export type PatternStatus = 'emerging' | 'repeated' | 'established' | 'contradicted' | 'inactive';

export type PatternConfidence = 'low' | 'medium' | 'high';

export type OccurrenceRelation = 'supports' | 'contradicts' | 'partially_supports';

export interface ApiCrossDecisionPattern {
  pattern_id: string;
  user_id: string;
  pattern_type: PatternType;
  title: string;
  statement: string;
  normalized_key: string;
  variable: string | null;
  domain: string | null;
  decision_types: string[];
  occurrence_count: number;
  supporting_decision_ids: string[];
  supporting_learning_ids: string[];
  supporting_experiment_ids: string[];
  supporting_threshold_ids: string[];
  contradicting_decision_ids: string[];
  evidence_count: number;
  confidence: PatternConfidence;
  confidence_basis: string;
  first_seen_at: string;
  last_seen_at: string;
  status: PatternStatus;
  created_at: string;
  updated_at: string;
}

export interface ApiPatternOccurrence {
  occurrence_id: string;
  pattern_id: string;
  user_id: string;
  decision_id: string;
  learning_id: string | null;
  source_type: string;
  source_id: string;
  observation: string;
  observed_at: string;
  relation: OccurrenceRelation;
  confidence: number;
}

export interface ApiCrossDecisionPatternDetail {
  pattern: ApiCrossDecisionPattern;
  occurrences: ApiPatternOccurrence[];
  supporting_occurrences: ApiPatternOccurrence[];
  contradicting_occurrences: ApiPatternOccurrence[];
}

export interface ApiCrossDecisionPatternListResponse {
  patterns: ApiCrossDecisionPattern[];
}

export interface ApiPatternRefreshResponse {
  user_id: string;
  patterns_created: number;
  patterns_updated: number;
  patterns_unchanged: number;
  total_patterns: number;
  refreshed_at: string;
}

/* -------------------------------------------------------------------------- *
 * Decision Intelligence Quality & Calibration Engine (REGRET ENGINE 2.0,
 * Step 24, backend/app/quality/schemas.py and backend/app/quality/calibration.py)
 * -------------------------------------------------------------------------- */

/** A category's (or the overall) grounding level - never a fabricated
 * percentage. `insufficient` is distinct from `weak`: it means there
 * wasn't even enough structured data to judge the category at all, not
 * that what exists is weak. */
export type QualityBand = 'strong' | 'moderate' | 'weak' | 'insufficient';

export type QualityCheckStatus = 'passed' | 'warning' | 'failed' | 'not_applicable';

export type QualityCheckSeverity = 'info' | 'low' | 'medium' | 'high' | 'critical';

export type QualityCheckCategory =
  | 'evidence'
  | 'assumption'
  | 'threshold'
  | 'experiment'
  | 'provenance'
  | 'consistency'
  | 'freshness'
  | 'historical'
  | 'completeness';

export interface ApiQualityCheck {
  check_id: string;
  category: QualityCheckCategory;
  name: string;
  status: QualityCheckStatus;
  severity: QualityCheckSeverity;
  message: string;
  related_entity_type: string | null;
  related_entity_id: string | null;
  evidence_ids: string[];
  recommendation: string | null;
  created_at: string;
}

export interface ApiQualityAssessment {
  quality_id: string;
  decision_id: string;
  analysis_run_id: string | null;
  user_id: string;
  overall_quality: QualityBand;
  evidence_quality: QualityBand;
  assumption_quality: QualityBand;
  threshold_quality: QualityBand;
  experiment_quality: QualityBand;
  provenance_quality: QualityBand;
  consistency_quality: QualityBand;
  freshness_quality: QualityBand;
  historical_learning_quality: QualityBand;
  blocking_issues: ApiQualityCheck[];
  warnings: ApiQualityCheck[];
  strengths: ApiQualityCheck[];
  checks: ApiQualityCheck[];
  generated_at: string;
  methodology_version: string;
}

/** A descriptive label for the shape of a user's own expectation-vs-
 * outcome history - never a claim of statistical significance. */
export type RecurringBias =
  | 'consistently_overoptimistic'
  | 'consistently_underoptimistic'
  | 'mixed'
  | 'insufficient_history'
  | 'no_detectable_bias';

/** Descriptive band for how much history backs a calibration
 * observation - never a fabricated confidence percentage. */
export type CalibrationEvidenceStrength =
  | 'limited_history'
  | 'emerging_calibration'
  | 'moderate_calibration_evidence'
  | 'strong_calibration_evidence';

export interface ApiCalibrationInsight {
  calibration_id: string;
  user_id: string;
  variable: string;
  expected_direction: string | null;
  observation_count: number;
  successful_count: number;
  unsuccessful_count: number;
  inconclusive_count: number;
  recurring_bias: RecurringBias;
  evidence_strength: CalibrationEvidenceStrength;
  confidence: number;
  supporting_decision_ids: string[];
  supporting_learning_ids: string[];
  explanation: string;
  created_at: string;
  updated_at: string;
}

/* -------------------------------------------------------------------------- *
 * Adaptive Decision Interview Agent (REGRET ENGINE 2.0, Step 27,
 * backend/app/interview/schemas.py)
 * -------------------------------------------------------------------------- */

export type InterviewStatus =
  | 'not_started'
  | 'active'
  | 'awaiting_answer'
  | 'ready'
  | 'completed'
  | 'user_stopped'
  | 'blocked'
  | 'failed';

export type InterviewTurnRole = 'user' | 'regret';

/** What TOPIC a question/answer is about - never chain-of-thought, just
 * a closed label REGRET uses to decide what to ask next. */
export type InterviewQuestionType =
  | 'clarification'
  | 'goal'
  | 'constraint'
  | 'belief'
  | 'uncertainty'
  | 'alternative'
  | 'commitment'
  | 'evidence'
  | 'stakeholder'
  | 'priority'
  | 'validation'
  | 'readiness';

/** Deterministic, structured-completeness readiness band - NEVER a
 * fabricated confidence score. See the backend's own
 * `app.interview.state.compute_readiness`. */
export type InterviewReadinessLevel = 'early' | 'enough' | 'ready';

export interface ApiExtractedFields {
  desired_outcome: string | null;
  constraints: string[];
  beliefs: string[];
  uncertainties: string[];
  alternatives: string[];
  commitments: string[];
  stakeholders: string[];
  important_variables: string[];
  evidence_mentions: string[];
  discovered_assumptions: string[];
  discovered_unknowns: string[];
}

export interface ApiDecisionInterviewState {
  interview_id: string;
  decision_id: string;
  user_id: string;
  status: InterviewStatus;
  turn_number: number;
  max_turns: number;
  decision_text: string;
  decision_type: string | null;
  selected_categories: string[];
  desired_outcome: string | null;
  constraints: string[];
  beliefs: string[];
  uncertainties: string[];
  alternatives: string[];
  commitments: string[];
  stakeholders: string[];
  important_variables: string[];
  evidence_summary: string[];
  discovered_assumptions: string[];
  discovered_unknowns: string[];
  questions_asked: InterviewQuestionType[];
  answers: string[];
  current_question: string | null;
  readiness: InterviewReadinessLevel;
  readiness_reason: string;
  created_at: string;
  updated_at: string;
}

/** The structured output of a completed/skipped interview - the input
 * to the EXISTING Decision Analyzer, never a replacement for it, and
 * never itself a verdict on the decision. */
export interface ApiDecisionSnapshot {
  decision: string;
  goal: string | null;
  constraints: string[];
  commitments: string[];
  beliefs: string[];
  uncertainties: string[];
  alternatives: string[];
  evidence: string[];
  important_variables: string[];
  stakeholders: string[];
  decision_criteria: string[];
  missing_information: string[];
  interview_summary: string;
}

export interface ApiStartInterviewRequest {
  selected_categories?: string[];
}

export interface ApiStartInterviewResponse {
  interview_id: string;
  first_question: string;
  state: ApiDecisionInterviewState;
}

export interface ApiRespondRequest {
  message: string;
  /** Optional idempotency guard - the `turn_number` the caller last saw
   * (mirrors `ApiDecisionUpdate.expected_updated_at`'s own optimistic-
   * concurrency pattern). Omit for a simple, unconditional request. */
  expected_turn_number?: number;
}

export interface ApiRespondResponse {
  response: string;
  extracted_fields: ApiExtractedFields;
  current_state: ApiDecisionInterviewState;
  next_question: string | null;
  readiness: InterviewReadinessLevel;
  turn_number: number;
  suggested_chips: string[];
  /** False only when the Interview Agent's own call failed this turn
   * and a deterministic fallback question was used instead - the UI
   * uses this to show "REGRET couldn't continue the interview, but you
   * can continue with the information you've already provided," never
   * a silent swap. */
  agent_available: boolean;
}

export interface ApiCompleteInterviewResponse {
  snapshot: ApiDecisionSnapshot;
  readiness: InterviewReadinessLevel;
  missing_information: string[];
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
