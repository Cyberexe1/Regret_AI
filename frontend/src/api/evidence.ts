/**
 * Evidence endpoints - mirrors app/api/routes/evidence.py exactly.
 *
 * Uploads use multipart/form-data with field name `file` (never JSON with
 * base64/inline file contents), matching the backend's exact contract.
 */

import { apiClient, type RequestOptions } from './client';
import type { ApiEvidence } from './types';

export function uploadEvidence(
  decisionId: string,
  file: File,
  options?: RequestOptions,
): Promise<ApiEvidence> {
  const form = new FormData();
  form.append('file', file);
  return apiClient.postForm<ApiEvidence>(`/decisions/${decisionId}/evidence`, form, options);
}

export function listEvidence(decisionId: string, options?: RequestOptions): Promise<ApiEvidence[]> {
  return apiClient.get<ApiEvidence[]>(`/decisions/${decisionId}/evidence`, options);
}

export function getEvidence(evidenceId: string, options?: RequestOptions): Promise<ApiEvidence> {
  return apiClient.get<ApiEvidence>(`/evidence/${evidenceId}`, options);
}

export function deleteEvidence(evidenceId: string, options?: RequestOptions): Promise<void> {
  return apiClient.delete<void>(`/evidence/${evidenceId}`, options);
}
