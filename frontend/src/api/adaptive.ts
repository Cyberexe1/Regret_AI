/**
 * Adaptive Experiment Loop API (REGRET ENGINE 2.0, Step 21).
 *
 * Mirrors `app.api.routes.adaptive` exactly: nested under a decision, one
 * read for the current state, one for the full history, one write to
 * advance to the next logical state (idempotent - see the backend
 * route's own docstring), and one write to let the user manually stop
 * the loop.
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type { ApiAdaptiveAdvanceResponse, ApiAdaptiveExperimentState } from './types';

export function getAdaptiveState(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiAdaptiveExperimentState> {
  return apiClient.get<ApiAdaptiveExperimentState>(`/decisions/${decisionId}/adaptive`, options);
}

export function listAdaptiveHistory(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiAdaptiveExperimentState[]> {
  return apiClient.get<ApiAdaptiveExperimentState[]>(
    `/decisions/${decisionId}/adaptive/history`,
    options,
  );
}

export function advanceAdaptiveCycle(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiAdaptiveAdvanceResponse> {
  return apiClient.post<ApiAdaptiveAdvanceResponse>(
    `/decisions/${decisionId}/adaptive/advance`,
    undefined,
    options,
  );
}

export function stopAdaptiveLoop(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiAdaptiveExperimentState> {
  return apiClient.post<ApiAdaptiveExperimentState>(
    `/decisions/${decisionId}/adaptive/stop`,
    undefined,
    options,
  );
}
