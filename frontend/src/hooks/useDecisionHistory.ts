import { useMemo } from 'react';
import { decisions as allDecisions } from '@/data/decisions';
import { experiments as allExperiments } from '@/data/experiments';
import {
  DECISION_STATUS_LABELS,
  summariseDecision,
  type DecisionSummary,
} from '@/lib/decisionSummary';
import type { RiskLevel } from '@/types';

export const DECISION_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'low', label: 'Low Risk' },
  { id: 'medium', label: 'Medium Risk' },
  { id: 'high', label: 'High Risk' },
  { id: 'needs-validation', label: 'Needs Validation' },
  { id: 'decision-ready', label: 'Decision Ready' },
] as const;

export type DecisionFilterId = (typeof DECISION_FILTERS)[number]['id'];

export const DECISION_SORTS = [
  { value: 'updated', label: 'Recently updated' },
  { value: 'risk', label: 'Highest risk' },
  { value: 'oldest', label: 'Oldest' },
] as const;

export type DecisionSortId = (typeof DECISION_SORTS)[number]['value'];

const RISK_WEIGHT: Record<RiskLevel, number> = { high: 0, medium: 1, low: 2 };

function matchesFilter(summary: DecisionSummary, filter: DecisionFilterId): boolean {
  switch (filter) {
    case 'all':
      return true;
    case 'low':
    case 'medium':
    case 'high':
      return summary.risk === filter;
    case 'needs-validation':
      return summary.statusLabel === DECISION_STATUS_LABELS.needsValidation;
    case 'decision-ready':
      return summary.statusLabel === DECISION_STATUS_LABELS.decisionReady;
  }
}

export interface DecisionHistoryOptions {
  query: string;
  filter: DecisionFilterId;
  sort: DecisionSortId;
}

export interface DecisionHistory {
  /** Rows after search, filter and sort. */
  rows: DecisionSummary[];
  /** Total in the workspace, ignoring search and filters. */
  totalCount: number;
  /** True when the workspace itself is empty, not just the current view. */
  isWorkspaceEmpty: boolean;
}

/**
 * Builds the history rows and applies search, filtering and sorting. Kept out of
 * the page so the page stays presentational.
 */
export function useDecisionHistory({
  query,
  filter,
  sort,
}: DecisionHistoryOptions): DecisionHistory {
  const summaries = useMemo(
    () => allDecisions.map((decision) => summariseDecision(decision, allExperiments)),
    [],
  );

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();

    const filtered = summaries
      .filter((summary) => matchesFilter(summary, filter))
      .filter((summary) => {
        if (!needle) return true;
        const { title, statement, id } = summary.decision;
        return (
          title.toLowerCase().includes(needle) ||
          statement.toLowerCase().includes(needle) ||
          id.toLowerCase().includes(needle)
        );
      });

    return filtered.toSorted((a, b) => {
      if (sort === 'oldest') {
        return a.decision.createdAt.localeCompare(b.decision.createdAt);
      }
      if (sort === 'risk') {
        const byRisk = RISK_WEIGHT[a.risk] - RISK_WEIGHT[b.risk];
        if (byRisk !== 0) return byRisk;
        // Within a band, the more exposed decision first.
        const exposure =
          (b.decision.analysis?.regretIndex ?? 0) - (a.decision.analysis?.regretIndex ?? 0);
        return exposure !== 0
          ? exposure
          : b.decision.updatedAt.localeCompare(a.decision.updatedAt);
      }
      return b.decision.updatedAt.localeCompare(a.decision.updatedAt);
    });
  }, [summaries, query, filter, sort]);

  return {
    rows,
    totalCount: summaries.length,
    isWorkspaceEmpty: summaries.length === 0,
  };
}
