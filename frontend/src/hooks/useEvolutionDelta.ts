import { evolutionApi } from '@/api';
import type { ApiDecisionDelta } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches the structured "what changed?" delta for one specific
 * evolution event (REGRET ENGINE 2.0, Step 22) -
 * `GET /decisions/{id}/evolution/{event_id}/delta`. Powers
 * `DecisionDeltaCard` when a user opens a timeline event's detail panel.
 * `undefined` eventId (nothing selected yet) is the normal "nothing to
 * show" case, not an error.
 */
export function useEvolutionDelta(decisionId: string | undefined, eventId: string | undefined) {
  return useAsync<ApiDecisionDelta | null>(
    async (signal) => {
      if (!decisionId || !eventId) return null;
      return evolutionApi.getDecisionEvolutionDelta(decisionId, eventId, { signal });
    },
    [decisionId, eventId],
  );
}
