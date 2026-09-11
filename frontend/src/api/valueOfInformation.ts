/**
 * Value-of-Information API (REGRET ENGINE 2.0, Step 20).
 *
 * Mirrors backend/app/api/routes/value_of_information.py exactly. Reads
 * are cheap (the most recently computed, already-persisted analysis);
 * `recompute` is the only write, and it never overwrites a previous
 * analysis - see the backend route's own docstring for the versioning
 * guarantee.
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type { ApiValueOfInformationAnalysis } from './types';

export function getValueOfInformation(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiValueOfInformationAnalysis> {
  return apiClient.get<ApiValueOfInformationAnalysis>(
    `/decisions/${decisionId}/value-of-information`,
    options,
  );
}

export function recomputeValueOfInformation(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiValueOfInformationAnalysis> {
  return apiClient.post<ApiValueOfInformationAnalysis>(
    `/decisions/${decisionId}/value-of-information/recompute`,
    undefined,
    options,
  );
}
