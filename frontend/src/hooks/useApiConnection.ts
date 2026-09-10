import { API_BASE_URL } from '@/api/client';
import { healthApi } from '@/api';
import type { ApiReadinessResponse } from '@/api/types';
import { useAsync } from './useAsync';

export interface ApiConnectionState {
  baseUrl: string;
  readiness: ApiReadinessResponse | null;
  isConnected: boolean;
}

/**
 * Reports whether the frontend can actually reach the FastAPI backend,
 * using the real `GET /api/v1/ready` endpoint - never a hardcoded "connected"
 * status. Shown on the Settings page. Never displays AWS credentials,
 * API keys, or other secret environment variables - only the configured
 * base URL and the backend's own readiness payload.
 */
export function useApiConnection() {
  const state = useAsync<ApiReadinessResponse>((signal) => healthApi.getReadiness({ signal }), []);
  return {
    baseUrl: API_BASE_URL,
    readiness: state.data,
    isConnected: state.status === 'success',
    ...state,
  };
}
