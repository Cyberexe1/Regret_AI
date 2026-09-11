import { useCallback, useState } from 'react';
import { adaptiveApi } from '@/api';
import type { ApiAdaptiveAdvanceResponse, ApiAdaptiveExperimentState } from '@/api/types';
import { describeApiError } from '@/lib/apiError';

export interface AdaptiveActionsState {
  isAdvancing: boolean;
  isStopping: boolean;
  error: { message: string; requestId: string | null } | null;
}

export interface AdaptiveActions extends AdaptiveActionsState {
  advance: (decisionId: string) => Promise<ApiAdaptiveAdvanceResponse | null>;
  stop: (decisionId: string) => Promise<ApiAdaptiveExperimentState | null>;
  reset: () => void;
}

/**
 * Owns `POST /decisions/{id}/adaptive/advance` and
 * `POST /decisions/{id}/adaptive/stop` submission state - mirrors
 * `useSubmitExperimentResult`'s shape. Both calls are safe to retry:
 * `advance` is idempotent on the backend (calling it again with no new
 * evidence just returns the existing state with `outcome=no_change`),
 * and `stop` is a no-op if the loop was never started.
 */
export function useAdaptiveActions(): AdaptiveActions {
  const [state, setState] = useState<AdaptiveActionsState>({
    isAdvancing: false,
    isStopping: false,
    error: null,
  });

  const advance = useCallback(async (decisionId: string) => {
    setState((current) => ({ ...current, isAdvancing: true, error: null }));
    try {
      const response = await adaptiveApi.advanceAdaptiveCycle(decisionId);
      setState((current) => ({ ...current, isAdvancing: false }));
      return response;
    } catch (error) {
      setState({ isAdvancing: false, isStopping: false, error: describeApiError(error) });
      return null;
    }
  }, []);

  const stop = useCallback(async (decisionId: string) => {
    setState((current) => ({ ...current, isStopping: true, error: null }));
    try {
      const response = await adaptiveApi.stopAdaptiveLoop(decisionId);
      setState((current) => ({ ...current, isStopping: false }));
      return response;
    } catch (error) {
      setState({ isAdvancing: false, isStopping: false, error: describeApiError(error) });
      return null;
    }
  }, []);

  const reset = useCallback(() => setState({ isAdvancing: false, isStopping: false, error: null }), []);

  return { ...state, advance, stop, reset };
}
