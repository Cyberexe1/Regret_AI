/** Experiment endpoints - mirrors app/api/routes/experiments.py exactly. */

import { apiClient, type RequestOptions } from './client';
import type {
  ApiExperiment,
  ApiExperimentResult,
  ApiExperimentResultCreate,
  ApiExperimentResultResponse,
} from './types';

export function listExperimentsForDecision(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiExperiment[]> {
  return apiClient.get<ApiExperiment[]>(`/decisions/${decisionId}/experiments`, options);
}

export function listExperimentResultsForDecision(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiExperimentResult[]> {
  return apiClient.get<ApiExperimentResult[]>(`/decisions/${decisionId}/experiment-results`, options);
}

export function getExperiment(experimentId: string, options?: RequestOptions): Promise<ApiExperiment> {
  return apiClient.get<ApiExperiment>(`/experiments/${experimentId}`, options);
}

export function submitExperimentResult(
  experimentId: string,
  payload: ApiExperimentResultCreate,
  options?: RequestOptions,
): Promise<ApiExperimentResultResponse> {
  return apiClient.post<ApiExperimentResultResponse>(
    `/experiments/${experimentId}/results`,
    payload,
    options,
  );
}

export function listExperimentResults(
  experimentId: string,
  options?: RequestOptions,
): Promise<ApiExperimentResult[]> {
  return apiClient.get<ApiExperimentResult[]>(`/experiments/${experimentId}/results`, options);
}
