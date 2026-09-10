import { analysisApi } from '@/api';
import type { ApiReEvaluation } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches a single re-evaluation by id from the decision's full
 * re-evaluation history (`GET /decisions/{id}/reevaluations`) - there is
 * no `GET /reevaluations/{id}` endpoint, so this filters the list rather
 * than inventing one.
 */
export function useReevaluation(decisionId: string | undefined, reevaluationId: string | undefined) {
  return useAsync<ApiReEvaluation | null>(
    async (signal) => {
      if (!decisionId || !reevaluationId) return null;
      const reevaluations = await analysisApi.listReevaluations(decisionId, { signal });
      return reevaluations.find((r) => r.id === reevaluationId) ?? null;
    },
    [decisionId, reevaluationId],
  );
}
