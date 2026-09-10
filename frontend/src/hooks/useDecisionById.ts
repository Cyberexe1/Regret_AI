import { decisionsApi } from '@/api';
import type { ApiDecision } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches a single decision by its real, server-assigned id. Replaces the
 * old `useDecision`, which resolved against a static in-memory array -
 * every decision now comes from `GET /decisions/{id}`.
 */
export function useDecisionById(id: string | undefined) {
  return useAsync<ApiDecision>(
    (signal) => {
      if (!id) return Promise.reject(new Error('No decision id provided.'));
      return decisionsApi.getDecision(id, { signal });
    },
    [id],
  );
}
