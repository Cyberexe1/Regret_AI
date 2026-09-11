import { adaptiveApi } from '@/api';
import type { ApiAdaptiveExperimentState } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches every adaptive-loop state ever recorded for a decision, oldest
 * first (`GET /decisions/{id}/adaptive/history`) - the full validation-
 * journey history (Experiment 1 -> Result -> Learning -> Experiment 2 ->
 * ...). An empty array is the normal state before the loop has ever been
 * started, never an error.
 */
export function useAdaptiveHistory(decisionId: string | undefined) {
  return useAsync<ApiAdaptiveExperimentState[]>(
    async (signal) => {
      if (!decisionId) return [];
      return adaptiveApi.listAdaptiveHistory(decisionId, { signal });
    },
    [decisionId],
  );
}
