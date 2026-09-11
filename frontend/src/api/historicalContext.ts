/**
 * Decision Similarity & Historical Insight API (REGRET ENGINE 2.0).
 *
 * Read-only - mirrors backend/app/api/routes/historical_context.py
 * exactly. Historical context is computed on read (deterministic,
 * user-scoped similarity scoring over the caller's own past decisions -
 * see the backend module's docstring), never created/updated directly
 * by the frontend.
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type { ApiDecisionCreate, ApiHistoricalContext } from './types';

export function getHistoricalContext(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiHistoricalContext> {
  return apiClient.get<ApiHistoricalContext>(`/decisions/${decisionId}/historical-context`, options);
}

/**
 * Preview historical context for a decision that has not been created
 * yet - powers the NewDecisionPage "Relevant from your past decisions"
 * section, where the user is still typing and no decision id exists.
 * Nothing is persisted server-side; see
 * app/api/routes/historical_context.py::preview_historical_context.
 */
export function previewHistoricalContext(
  draft: ApiDecisionCreate,
  options?: RequestOptions,
): Promise<ApiHistoricalContext> {
  return apiClient.post<ApiHistoricalContext>('/decisions/historical-context/preview', draft, options);
}
