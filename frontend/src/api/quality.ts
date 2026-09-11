/**
 * Decision Intelligence Quality & Calibration Engine API (REGRET ENGINE
 * 2.0, Step 24).
 *
 * Mirrors `app.api.routes.quality` exactly. Reads never trigger a new
 * check - `runQualityCheck`/`refreshCalibration` are the only writes,
 * and calibration is always scoped to the caller's own decisions (there
 * is no parameter anywhere here that could target a different user).
 */

import { apiClient } from './client';
import type { RequestOptions } from './client';
import type { ApiCalibrationInsight, ApiQualityAssessment } from './types';

export function getDecisionQuality(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiQualityAssessment> {
  return apiClient.get<ApiQualityAssessment>(`/decisions/${decisionId}/quality`, options);
}

export function listDecisionQualityHistory(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiQualityAssessment[]> {
  return apiClient.get<ApiQualityAssessment[]>(`/decisions/${decisionId}/quality/history`, options);
}

export function runQualityCheck(
  decisionId: string,
  options?: RequestOptions,
): Promise<ApiQualityAssessment> {
  return apiClient.post<ApiQualityAssessment>(
    `/decisions/${decisionId}/quality/check`,
    undefined,
    options,
  );
}

export function listCalibrationInsights(
  options?: RequestOptions,
): Promise<ApiCalibrationInsight[]> {
  return apiClient.get<ApiCalibrationInsight[]>('/learning/calibration', options);
}

export function getCalibrationInsightForVariable(
  variable: string,
  options?: RequestOptions,
): Promise<ApiCalibrationInsight> {
  return apiClient.get<ApiCalibrationInsight>(
    `/learning/calibration/${encodeURIComponent(variable)}`,
    options,
  );
}

export function refreshCalibrationInsights(
  options?: RequestOptions,
): Promise<ApiCalibrationInsight[]> {
  return apiClient.post<ApiCalibrationInsight[]>('/learning/calibration/refresh', undefined, options);
}
