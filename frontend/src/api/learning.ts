/**
 * Cross-Decision Learning Engine API (REGRET ENGINE 2.0, Step 23).
 *
 * Mirrors `app.api.routes.learning` exactly. Reads never trigger
 * detection - `refreshPatterns` is the only write, and it is always
 * scoped to the caller's own decisions (there is no parameter anywhere
 * here that could target a different user).
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type {
  ApiCrossDecisionPatternDetail,
  ApiCrossDecisionPatternListResponse,
  ApiPatternRefreshResponse,
  PatternStatus,
  PatternType,
} from './types';

export interface ListPatternsFilters {
  patternType?: PatternType;
  status?: PatternStatus;
  domain?: string;
  variable?: string;
}

export function listPatterns(
  filters?: ListPatternsFilters,
  options?: RequestOptions,
): Promise<ApiCrossDecisionPatternListResponse> {
  return apiClient.get<ApiCrossDecisionPatternListResponse>('/learning/patterns', {
    ...options,
    query: {
      pattern_type: filters?.patternType,
      status: filters?.status,
      domain: filters?.domain,
      variable: filters?.variable,
    },
  });
}

export function getPatternDetail(
  patternId: string,
  options?: RequestOptions,
): Promise<ApiCrossDecisionPatternDetail> {
  return apiClient.get<ApiCrossDecisionPatternDetail>(`/learning/patterns/${patternId}`, options);
}

export function refreshPatterns(options?: RequestOptions): Promise<ApiPatternRefreshResponse> {
  return apiClient.post<ApiPatternRefreshResponse>('/learning/patterns/refresh', undefined, options);
}

export function getPatternsForDecision(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiCrossDecisionPatternListResponse> {
  return apiClient.get<ApiCrossDecisionPatternListResponse>(
    `/decisions/${decisionId}/patterns`,
    options,
  );
}
