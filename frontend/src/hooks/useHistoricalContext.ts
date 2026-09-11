import { historicalContextApi } from '@/api';
import type { ApiHistoricalContext } from '@/api/types';
import { useAsync } from './useAsync';

const EMPTY_CONTEXT: ApiHistoricalContext = {
  found: false,
  relevant_decisions: [],
  relevant_decisions_count: 0,
  relevant_learnings: [],
  recurring_variables: [],
  previously_failed_assumptions: [],
  previously_validated_thresholds: [],
  unresolved_patterns: [],
  warnings: [],
};

/**
 * Fetches a decision's Decision Similarity + Historical Insight context
 * (REGRET ENGINE 2.0) - `GET /decisions/{id}/historical-context`. Returns
 * a valid, empty-shaped (`found: false`) response for a decision with no
 * id yet, never an error - see the backend route's own docstring.
 */
export function useHistoricalContext(decisionId: string | undefined) {
  return useAsync<ApiHistoricalContext>(
    async (signal) => {
      if (!decisionId) return EMPTY_CONTEXT;
      return historicalContextApi.getHistoricalContext(decisionId, { signal });
    },
    [decisionId],
  );
}
