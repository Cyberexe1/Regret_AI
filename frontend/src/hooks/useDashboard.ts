import { decisionsApi, experimentsApi } from '@/api';
import type { ApiDecision, ApiExperiment } from '@/api/types';
import { useAsync } from './useAsync';

export interface DashboardData {
  decisions: ApiDecision[];
  /** Experiments for the decisions currently loaded, keyed by decision id. */
  experimentsByDecisionId: Map<string, ApiExperiment[]>;
}

const RECENT_DECISIONS_LIMIT = 20;

/**
 * Loads the current user's most recent decisions and, for each, its
 * experiments - the real data every dashboard card derives its counts
 * from. Replaces the old static `data/dashboard.ts` module entirely; no
 * value shown on the dashboard is fabricated anymore.
 *
 * Bounded to the most recent `RECENT_DECISIONS_LIMIT` decisions (cursor
 * pagination's first page) - the dashboard is a snapshot, not the full
 * archive (that's Decision History, which paginates properly).
 */
export function useDashboard() {
  return useAsync<DashboardData>(async (signal) => {
    const { items: decisions } = await decisionsApi.listDecisions(
      { limit: RECENT_DECISIONS_LIMIT },
      { signal },
    );

    const experimentsByDecisionId = new Map<string, ApiExperiment[]>();
    await Promise.all(
      decisions.map(async (decision) => {
        try {
          const experiments = await experimentsApi.listExperimentsForDecision(decision.id, { signal });
          experimentsByDecisionId.set(decision.id, experiments);
        } catch {
          // A single decision's experiments failing to load must not blank
          // the whole dashboard - it simply shows zero experiments for that
          // decision rather than surfacing a page-level error.
          experimentsByDecisionId.set(decision.id, []);
        }
      }),
    );

    return { decisions, experimentsByDecisionId };
  }, []);
}
