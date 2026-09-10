/** External research endpoints - mirrors app/api/routes/research.py exactly. */

import { apiClient, type RequestOptions } from './client';
import type { ApiExternalEvidence } from './types';

export function listExternalEvidence(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiExternalEvidence[]> {
  return apiClient.get<ApiExternalEvidence[]>(`/decisions/${decisionId}/external-evidence`, options);
}
