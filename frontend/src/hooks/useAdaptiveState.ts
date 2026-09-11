import { adaptiveApi } from '@/api';
import { isNotFoundError } from '@/lib/apiError';
import type { ApiAdaptiveExperimentState } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches a decision's current Adaptive Experiment Loop state
 * (REGRET ENGINE 2.0, Step 21) - `GET /decisions/{id}/adaptive`. Returns
 * `null` (never an error state) both when the decision has no id yet
 * and when the backend returns 404 (the loop has never been started for
 * this decision yet) - both are the normal "nothing to show yet" case.
 */
export function useAdaptiveState(decisionId: string | undefined) {
  return useAsync<ApiAdaptiveExperimentState | null>(
    async (signal) => {
      if (!decisionId) return null;
      try {
        return await adaptiveApi.getAdaptiveState(decisionId, { signal });
      } catch (error) {
        if (isNotFoundError(error)) return null;
        throw error;
      }
    },
    [decisionId],
  );
}
