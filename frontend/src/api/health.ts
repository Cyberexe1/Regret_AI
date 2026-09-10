/** Health/readiness endpoints - mirrors app/api/routes/health.py exactly. */

import { apiClient, type RequestOptions } from './client';
import type { ApiHealthResponse, ApiReadinessResponse } from './types';

export function getHealth(options?: RequestOptions): Promise<ApiHealthResponse> {
  return apiClient.get<ApiHealthResponse>('/health', options);
}

export function getReadiness(options?: RequestOptions): Promise<ApiReadinessResponse> {
  return apiClient.get<ApiReadinessResponse>('/ready', options);
}
