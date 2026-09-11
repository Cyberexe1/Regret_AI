/**
 * REGRET ENGINE 2.0: pure mapping from the real backend Historical
 * Context response (`ApiHistoricalContext`) into presentational view
 * models - mirrors `buildDecisionMemory.ts` exactly.
 *
 * Nothing here is fabricated: `relevancePercent` is a deterministic,
 * explainable similarity score, rendered as a percentage for display but
 * NEVER labelled or described as a probability anywhere in this file or
 * the components that consume it - see the backend's own
 * `similarity_schemas.py` module docstring for why that distinction is
 * load-bearing, not cosmetic. Every insight is traceable to a real,
 * already-persisted `MemoryLearning` via `sourceDecisionId`/`id`.
 */
import type { ApiHistoricalContext, ApiHistoricalInsight, ApiSimilarityScore, LearningType } from '@/api/types';
import { learningTypeLabel, learningTypeTone } from '@/lib/buildDecisionMemory';
import { formatRelative } from '@/lib/format';
import type { HistoricalContextSummary, HistoricalInsightRow, RelatedDecisionRow } from '@/types/report';

/** Shared empty state, used by every page that renders
 * `HistoricalInsightsPanel` before its data has loaded. */
export const EMPTY_HISTORICAL_SUMMARY: HistoricalContextSummary = {
  found: false,
  relevantDecisions: [],
  insights: [],
  recurringVariables: [],
  previouslyFailedAssumptions: [],
  previouslyValidatedThresholds: [],
  warnings: [],
};

const VALIDATED_LEARNING_TYPES = new Set<LearningType>([
  'assumption_validated',
  'threshold_validated',
]);

const FEATURE_LABELS: Record<string, string> = {
  decision_text_similarity: 'Similar wording',
  assumption_overlap: 'Overlapping assumptions',
  key_variable_overlap: 'Shared key variable',
  budget_similarity: 'Comparable budget',
  risk_tolerance_match: 'Same risk tolerance',
  location_match: 'Same location',
};

function featureLabel(feature: string): string {
  return FEATURE_LABELS[feature] ?? feature;
}

function buildRelatedDecisionRow(
  score: ApiSimilarityScore,
  titleById: Map<string, string>,
): RelatedDecisionRow {
  return {
    decisionId: score.decision_id,
    title: titleById.get(score.decision_id) ?? 'A past decision',
    relevancePercent: Math.round(score.score * 100),
    matchedFeatureLabels: score.matched_features.map(featureLabel),
    explanation: score.explanation,
  };
}

function buildInsightRow(insight: ApiHistoricalInsight): HistoricalInsightRow {
  return {
    id: insight.insight_id,
    statement: insight.statement,
    typeLabel: learningTypeLabel(insight.learning_type),
    typeTone: learningTypeTone(insight.learning_type),
    isValidated: VALIDATED_LEARNING_TYPES.has(insight.learning_type),
    relevancePercent: Math.round(insight.relevance_score * 100),
    sourceDecisionId: insight.source_decision_id,
    observedValue: insight.observed_value,
    expectedValue: insight.expected_value,
    createdAtLabel: formatRelative(insight.created_at),
  };
}

/**
 * Builds the full historical-context view model for one decision.
 * `titleById`, if provided, resolves a related decision's real title for
 * display (e.g. from the dashboard's already-loaded decision list) -
 * falls back to a generic label when the title isn't known locally,
 * never fabricating one.
 */
export function buildHistoricalContext(
  response: ApiHistoricalContext,
  titleById: Map<string, string> = new Map(),
): HistoricalContextSummary {
  return {
    found: response.found,
    relevantDecisions: response.relevant_decisions.map((score) =>
      buildRelatedDecisionRow(score, titleById),
    ),
    insights: response.relevant_learnings.map(buildInsightRow),
    recurringVariables: response.recurring_variables,
    previouslyFailedAssumptions: response.previously_failed_assumptions,
    previouslyValidatedThresholds: response.previously_validated_thresholds,
    warnings: response.warnings,
  };
}
