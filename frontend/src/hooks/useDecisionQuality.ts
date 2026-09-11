import { qualityApi } from '@/api';
import { isNotFoundError } from '@/lib/apiError';
import type { ApiQualityAssessment } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches the most recently computed quality assessment for a decision
 * (REGRET ENGINE 2.0, Step 24) - `GET /decisions/{id}/quality`. Returns
 * `null` (never an error state) both when the decision has no id yet
 * and when the backend returns 404 (no quality check has ever been run
 * for this decision yet) - both are the normal "nothing to show yet"
 * case, mirroring `useAdaptiveState`.
 */
export function useDecisionQuality(decisionId: string | undefined) {
  return useAsync<ApiQualityAssessment | null>(
    async (signal) => {
      if (!decisionId) return null;
      try {
        return await qualityApi.getDecisionQuality(decisionId, { signal });
      } catch (error) {
        if (isNotFoundError(error)) return null;
        throw error;
      }
    },
    [decisionId],
  );
}
