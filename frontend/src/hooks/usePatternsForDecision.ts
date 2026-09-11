import { learningApi } from '@/api';
import type { ApiCrossDecisionPattern } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches the patterns relevant to one specific decision
 * (REGRET ENGINE 2.0, Step 23) - `GET /decisions/{id}/patterns`. An
 * empty list is the normal state before `POST /learning/patterns/refresh`
 * has ever run, never an error.
 */
export function usePatternsForDecision(decisionId: string | undefined) {
  return useAsync<ApiCrossDecisionPattern[]>(
    async (signal) => {
      if (!decisionId) return [];
      const response = await learningApi.getPatternsForDecision(decisionId, { signal });
      return response.patterns;
    },
    [decisionId],
  );
}
