/** Decision endpoints - mirrors app/api/routes/decisions.py exactly. */

import { apiClient, type RequestOptions } from './client';
import type {
  ApiDecision,
  ApiDecisionCreate,
  ApiDecisionListResponse,
  ApiDecisionUpdate,
} from './types';

export function createDecision(payload: ApiDecisionCreate, options?: RequestOptions): Promise<ApiDecision> {
  return apiClient.post<ApiDecision>('/decisions', payload, options);
}

export function listDecisions(
  params: { limit?: number; cursor?: string | null } = {},
  options?: RequestOptions,
): Promise<ApiDecisionListResponse> {
  return apiClient.get<ApiDecisionListResponse>('/decisions', {
    ...options,
    query: { limit: params.limit, cursor: params.cursor },
  });
}

export function getDecision(decisionId: string, options?: RequestOptions): Promise<ApiDecision> {
  return apiClient.get<ApiDecision>(`/decisions/${decisionId}`, options);
}

export function updateDecision(
  decisionId: string,
  payload: ApiDecisionUpdate,
  options?: RequestOptions,
): Promise<ApiDecision> {
  return apiClient.patch<ApiDecision>(`/decisions/${decisionId}`, payload, options);
}

export function deleteDecision(decisionId: string, options?: RequestOptions): Promise<void> {
  return apiClient.delete<void>(`/decisions/${decisionId}`, options);
}
