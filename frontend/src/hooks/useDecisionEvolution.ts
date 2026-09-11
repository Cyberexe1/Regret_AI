import { evolutionApi } from '@/api';
import type { ApiDecisionEvolution } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches a decision's complete evolution timeline in one bounded call
 * (REGRET ENGINE 2.0, Step 22) - `GET /decisions/{id}/evolution`. Never
 * 404s once the decision itself exists (a brand-new decision simply has
 * a one-event timeline) - `undefined` decisionId is the only "nothing to
 * show yet" case handled here.
 */
export function useDecisionEvolution(decisionId: string | undefined) {
  return useAsync<ApiDecisionEvolution | null>(
    async (signal) => {
      if (!decisionId) return null;
      return evolutionApi.getDecisionEvolution(decisionId, { signal });
    },
    [decisionId],
  );
}
