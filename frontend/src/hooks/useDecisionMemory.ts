import { memoryApi } from '@/api';
import type { ApiDecisionMemoryResponse } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches a decision's full Decision Memory context (REGRET ENGINE 2.0):
 * the memory summary, its learnings, the real experiments/assessments it
 * references, and its current unresolved uncertainties - one call to
 * `GET /decisions/{id}/memory`. Returns a valid, empty-shaped response
 * (never an error) for a decision that hasn't been analyzed yet - see
 * the backend route's own docstring.
 */
export function useDecisionMemory(decisionId: string | undefined) {
  return useAsync<ApiDecisionMemoryResponse>(
    async (signal) => {
      if (!decisionId) {
        return { memory: null, learnings: [], experiments: [], assessments: [], unresolved_uncertainties: [] };
      }
      return memoryApi.getDecisionMemory(decisionId, { signal });
    },
    [decisionId],
  );
}
