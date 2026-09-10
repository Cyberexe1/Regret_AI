/**
 * Analysis endpoints - mirrors app/api/routes/analysis.py and
 * app/api/routes/decision_analysis_resources.py exactly.
 *
 * `startAnalysis` is a long-running, synchronous backend call (the request
 * blocks until the full ~9-stage pipeline reaches a terminal status) - see
 * backend README "Idempotency" section. Give it a generous timeout rather
 * than the client default.
 */

import { apiClient, type RequestOptions } from './client';
import type {
  ApiAnalysisRunResponse,
  ApiAnalysisRunStatusResponse,
  ApiAssumption,
  ApiBlindspot,
  ApiChallenge,
  ApiEvidenceFinding,
  ApiReEvaluation,
  ApiRegretScenario,
  ApiThreshold,
} from './types';

/** The backend's own `analysis_max_duration_seconds` default is 600s; give the
 * client a matching budget plus headroom for network latency. */
const ANALYSIS_TIMEOUT_MS = 620_000;

export function startAnalysis(decisionId: string, options?: RequestOptions): Promise<ApiAnalysisRunResponse> {
  return apiClient.post<ApiAnalysisRunResponse>(`/decisions/${decisionId}/analyze`, undefined, {
    timeoutMs: ANALYSIS_TIMEOUT_MS,
    ...options,
  });
}

export function getAnalysisStatus(
  decisionId: string,
  analysisRunId: string,
  options?: RequestOptions,
): Promise<ApiAnalysisRunStatusResponse> {
  return apiClient.get<ApiAnalysisRunStatusResponse>(
    `/decisions/${decisionId}/analysis/${analysisRunId}`,
    options,
  );
}

/**
 * Fetch the status of a decision's most recently created analysis run,
 * without knowing its id upfront - see
 * app/api/routes/analysis.py::get_latest_analysis_status. Used to poll a
 * run's live progress from a second, concurrent request while the
 * (synchronous) `startAnalysis` call above is still in flight.
 */
export function getLatestAnalysisStatus(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiAnalysisRunStatusResponse> {
  return apiClient.get<ApiAnalysisRunStatusResponse>(`/decisions/${decisionId}/analysis/latest`, options);
}

export function listAssumptions(decisionId: string, options?: RequestOptions): Promise<ApiAssumption[]> {
  return apiClient.get<ApiAssumption[]>(`/decisions/${decisionId}/assumptions`, options);
}

export function listBlindspots(decisionId: string, options?: RequestOptions): Promise<ApiBlindspot[]> {
  return apiClient.get<ApiBlindspot[]>(`/decisions/${decisionId}/blindspots`, options);
}

export function listEvidenceFindings(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiEvidenceFinding[]> {
  return apiClient.get<ApiEvidenceFinding[]>(`/decisions/${decisionId}/evidence-findings`, options);
}

export function listChallenges(decisionId: string, options?: RequestOptions): Promise<ApiChallenge[]> {
  return apiClient.get<ApiChallenge[]>(`/decisions/${decisionId}/challenges`, options);
}

export function listRegretScenarios(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiRegretScenario[]> {
  return apiClient.get<ApiRegretScenario[]>(`/decisions/${decisionId}/regret-scenarios`, options);
}

export function listThresholds(decisionId: string, options?: RequestOptions): Promise<ApiThreshold[]> {
  return apiClient.get<ApiThreshold[]>(`/decisions/${decisionId}/thresholds`, options);
}

export function listReevaluations(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiReEvaluation[]> {
  return apiClient.get<ApiReEvaluation[]>(`/decisions/${decisionId}/reevaluations`, options);
}
