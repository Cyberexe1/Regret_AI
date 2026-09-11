/**
 * REGRET ENGINE 2.0's Value-of-Information Engine (Step 20): pure mapping
 * from the real backend `ApiValueOfInformationAnalysis` response into a
 * presentational view model - mirrors `buildHistoricalContext.ts` and
 * `buildDecisionMemory.ts` exactly.
 *
 * Nothing here is fabricated. `barPercent` is derived ONLY from the
 * item's own qualitative `practical_value` band (a fixed, documented
 * mapping - never a raw score presented as if it were precise), purely
 * to drive the ranked bar-chart visual. `confidencePercent` is a real
 * backend float, explicitly labelled everywhere as "how much of this
 * score rests on real inputs" - never a probability.
 */
import type { ApiValueOfInformationAnalysis, ApiValueOfInformationItem, CostBand, ValueBand } from '@/api/types';
import { formatDays } from '@/lib/format';
import type { ValueOfInformationRow, ValueOfInformationSummary } from '@/types/report';
import type { Tone } from '@/types';

/** Shared empty state, used by every page that renders the VOI panel
 * before its data has loaded, or when no analysis exists yet. */
export const EMPTY_VOI_SUMMARY: ValueOfInformationSummary = {
  found: false,
  ranked: [],
  primaryUncertaintyId: null,
  whyThisIsPrimary: null,
  summary: '',
};

const VALUE_BAND_LABEL: Record<ValueBand, string> = {
  very_low: 'Very low',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  very_high: 'Very high',
  unknown: 'Unknown',
};

/** Higher practical/information value draws more visual attention - this
 * is a display convention only, never a claim about probability. */
const VALUE_BAND_TONE: Record<ValueBand, Tone> = {
  very_low: 'neutral',
  low: 'neutral',
  medium: 'info',
  high: 'warning',
  very_high: 'danger',
  unknown: 'neutral',
};

/** Fixed percentage each band maps to for the ranked bar visualization -
 * a display convention documented here, never presented as a precise
 * statistic anywhere in the UI. */
const VALUE_BAND_BAR_PERCENT: Record<ValueBand, number> = {
  unknown: 8,
  very_low: 15,
  low: 35,
  medium: 55,
  high: 78,
  very_high: 100,
};

const COST_BAND_LABEL: Record<CostBand, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  unknown: 'Not yet costed',
};

function capitalize(value: string | null): string {
  if (!value) return 'Unrated';
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ');
}

function historicalRelevanceLabel(value: ApiValueOfInformationItem['historical_relevance']): string | null {
  if (value === 'none') return null;
  return `${capitalize(value)} - seen in your past decisions`;
}

function buildRow(item: ApiValueOfInformationItem, index: number): ValueOfInformationRow {
  return {
    uncertaintyId: item.uncertainty_id,
    rank: String(index + 1).padStart(2, '0'),
    title: item.title,
    description: item.description,
    informationValueLabel: VALUE_BAND_LABEL[item.information_value],
    informationValueTone: VALUE_BAND_TONE[item.information_value],
    practicalValueLabel: VALUE_BAND_LABEL[item.practical_value],
    practicalValueTone: VALUE_BAND_TONE[item.practical_value],
    rationale: item.rationale,
    costLabel: COST_BAND_LABEL[item.estimated_test_cost],
    durationLabel: item.estimated_test_duration_days !== null ? formatDays(item.estimated_test_duration_days) : null,
    feasibilityLabel: capitalize(item.feasibility),
    reversibilityLabel: capitalize(item.reversibility),
    thresholdId: item.threshold_status === 'linked' ? (item.related_threshold_ids[0] ?? null) : null,
    thresholdStatusLabel:
      item.threshold_status === 'linked' ? 'Connected to a recorded threshold' : 'No threshold established yet',
    historicalRelevanceLabel: historicalRelevanceLabel(item.historical_relevance),
    confidencePercent: Math.round(item.confidence * 100),
    barPercent: VALUE_BAND_BAR_PERCENT[item.practical_value],
  };
}

/**
 * Builds the full "What should you test first?" view model from a real
 * `ApiValueOfInformationAnalysis` response. `found=false` (no analysis
 * computed yet, e.g. before the pipeline reaches the Threshold Engine
 * stage) is a normal, valid state - never an error.
 */
export function buildValueOfInformation(
  analysis: ApiValueOfInformationAnalysis | null,
): ValueOfInformationSummary {
  if (analysis === null || analysis.ranked_uncertainties.length === 0) {
    return EMPTY_VOI_SUMMARY;
  }

  return {
    found: true,
    ranked: analysis.ranked_uncertainties.map(buildRow),
    primaryUncertaintyId: analysis.primary_uncertainty_id,
    whyThisIsPrimary: analysis.why_this_is_primary,
    summary: analysis.summary,
  };
}
