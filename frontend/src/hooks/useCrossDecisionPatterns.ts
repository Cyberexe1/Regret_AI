import { learningApi } from '@/api';
import type { ApiCrossDecisionPattern } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches every cross-decision pattern currently recorded for the
 * caller's own decision history (REGRET ENGINE 2.0, Step 23) -
 * `GET /learning/patterns`. Never triggers a refresh itself; an empty
 * list is the normal state before `POST /learning/patterns/refresh` has
 * ever run.
 */
export function useCrossDecisionPatterns() {
  return useAsync<ApiCrossDecisionPattern[]>(async (signal) => {
    const response = await learningApi.listPatterns(undefined, { signal });
    return response.patterns;
  }, []);
}
