/**
 * Adaptive Decision Interview Agent API (REGRET ENGINE 2.0, Step 27).
 *
 * Mirrors `app.api.routes.interview` exactly. `startInterview` is
 * idempotent server-side (revisiting it for a decision that already
 * has an active interview returns that SAME interview), and
 * `respondToInterview` accepts an optional `expected_turn_number` guard
 * so a dropped-response retry can never be double-processed.
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type {
  ApiCompleteInterviewResponse,
  ApiDecisionInterviewState,
  ApiRespondRequest,
  ApiRespondResponse,
  ApiStartInterviewRequest,
  ApiStartInterviewResponse,
} from './types';

export function startInterview(
  decisionId: string,
  payload: ApiStartInterviewRequest = {},
  options?: RequestOptions,
): Promise<ApiStartInterviewResponse> {
  return apiClient.post<ApiStartInterviewResponse>(
    `/decisions/${decisionId}/interview/start`,
    payload,
    options,
  );
}

export function respondToInterview(
  interviewId: string,
  payload: ApiRespondRequest,
  options?: RequestOptions,
): Promise<ApiRespondResponse> {
  return apiClient.post<ApiRespondResponse>(`/interviews/${interviewId}/respond`, payload, options);
}

export function getInterview(
  interviewId: string,
  options?: RequestOptions,
): Promise<ApiDecisionInterviewState> {
  return apiClient.get<ApiDecisionInterviewState>(`/interviews/${interviewId}`, options);
}

export function completeInterview(
  interviewId: string,
  options?: RequestOptions,
): Promise<ApiCompleteInterviewResponse> {
  return apiClient.post<ApiCompleteInterviewResponse>(
    `/interviews/${interviewId}/complete`,
    undefined,
    options,
  );
}

export function skipInterview(
  interviewId: string,
  options?: RequestOptions,
): Promise<ApiCompleteInterviewResponse> {
  return apiClient.post<ApiCompleteInterviewResponse>(
    `/interviews/${interviewId}/skip`,
    undefined,
    options,
  );
}
