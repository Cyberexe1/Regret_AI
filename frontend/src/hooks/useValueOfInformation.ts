import { valueOfInformationApi } from '@/api';
import { isNotFoundError } from '@/lib/apiError';
import type { ApiValueOfInformationAnalysis } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches a decision's most recently computed Value-of-Information
 * analysis (REGRET ENGINE 2.0, Step 20) - `GET
 * /decisions/{id}/value-of-information`. Returns `null` (never an error
 * state) both when the decision has no id yet and when the backend
 * returns 404 (no analysis computed yet, e.g. before the pipeline
 * reaches the Threshold Engine stage) - both are the normal "nothing to
 * show yet" case.
 */
export function useValueOfInformation(decisionId: string | undefined) {
  return useAsync<ApiValueOfInformationAnalysis | null>(
    async (signal) => {
      if (!decisionId) return null;
      try {
        return await valueOfInformationApi.getValueOfInformation(decisionId, { signal });
      } catch (error) {
        if (isNotFoundError(error)) return null;
        throw error;
      }
    },
    [decisionId],
  );
}
