import { useMemo } from 'react';
import { decisions as allDecisions, findDecision } from '@/data/decisions';
import { experiments as allExperiments } from '@/data/experiments';
import type { Decision, DecisionDomain, DecisionStatus, Experiment } from '@/types';

export interface DecisionFilters {
  status?: DecisionStatus | 'all';
  domain?: DecisionDomain | 'all';
  /** Free-text match against title and statement. */
  query?: string;
}

/**
 * Reads from the local sample corpus. Kept behind a hook so the eventual data
 * source can be swapped without touching any page.
 */
export function useDecisions(filters: DecisionFilters = {}): Decision[] {
  const { status = 'all', domain = 'all', query = '' } = filters;

  return useMemo(() => {
    const needle = query.trim().toLowerCase();

    return allDecisions
      .filter((decision) => status === 'all' || decision.status === status)
      .filter((decision) => domain === 'all' || decision.domain === domain)
      .filter((decision) => {
        if (!needle) return true;
        return (
          decision.title.toLowerCase().includes(needle) ||
          decision.statement.toLowerCase().includes(needle)
        );
      })
      .toSorted((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }, [status, domain, query]);
}

export function useDecision(id: string | undefined): Decision | undefined {
  // Goes through `findDecision` so id aliases resolve in one place.
  return useMemo(() => (id ? findDecision(id) : undefined), [id]);
}

/** All experiments, or only those attached to one decision. */
export function useExperiments(decisionId?: string): Experiment[] {
  return useMemo(() => {
    const scoped = decisionId
      ? allExperiments.filter((experiment) => experiment.decisionId === decisionId)
      : allExperiments;

    return scoped.toSorted((a, b) => b.informationGain - a.informationGain);
  }, [decisionId]);
}
