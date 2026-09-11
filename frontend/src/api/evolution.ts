/**
 * Decision Evolution & Causal Timeline API (REGRET ENGINE 2.0, Step 22).
 *
 * Mirrors `app.api.routes.evolution` exactly: one bounded call returns
 * the complete timeline, current state, and major changes - no per-event
 * API calls are needed to render the whole "Decision Evolution" section
 * (see the backend route's own docstring).
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type { ApiDecisionDelta, ApiDecisionEvolution, ApiDecisionEvolutionEvent } from './types';

export function getDecisionEvolution(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiDecisionEvolution> {
  return apiClient.get<ApiDecisionEvolution>(`/decisions/${decisionId}/evolution`, options);
}

export function getDecisionEvolutionEvent(
  decisionId: string,
  eventId: string,
  options?: RequestOptions,
): Promise<ApiDecisionEvolutionEvent> {
  return apiClient.get<ApiDecisionEvolutionEvent>(
    `/decisions/${decisionId}/evolution/${eventId}`,
    options,
  );
}

export function getDecisionEvolutionDelta(
  decisionId: string,
  eventId: string,
  options?: RequestOptions,
): Promise<ApiDecisionDelta> {
  return apiClient.get<ApiDecisionDelta>(
    `/decisions/${decisionId}/evolution/${eventId}/delta`,
    options,
  );
}
