/**
 * Decision Memory API (REGRET ENGINE 2.0).
 *
 * Read-only - memory is never created/updated directly by the frontend;
 * it's a consequence of submitting an experiment result (see
 * `experimentsApi.submitExperimentResult`), which the backend already
 * updates memory from server-side. See backend/app/api/routes/memory.py.
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type { ApiDecisionMemoryResponse, ApiMemoryLearning } from './types';

export function getDecisionMemory(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiDecisionMemoryResponse> {
  return apiClient.get<ApiDecisionMemoryResponse>(`/decisions/${decisionId}/memory`, options);
}

export function listDecisionLearnings(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiMemoryLearning[]> {
  return apiClient.get<ApiMemoryLearning[]>(`/decisions/${decisionId}/learnings`, options);
}

export function getMemoryById(
  memoryId: string,
  options?: RequestOptions,
): Promise<ApiDecisionMemoryResponse> {
  return apiClient.get<ApiDecisionMemoryResponse>(`/memory/${memoryId}`, options);
}
