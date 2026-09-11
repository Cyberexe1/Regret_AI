import { qualityApi } from '@/api';
import type { ApiCalibrationInsight } from '@/api/types';
import { useAsync } from './useAsync';

/**
 * Fetches every calibration insight currently recorded for the caller's
 * own decision history (REGRET ENGINE 2.0, Step 24) -
 * `GET /learning/calibration`. Never triggers a refresh itself; an
 * empty list is the normal state before
 * `POST /learning/calibration/refresh` has ever run.
 */
export function useCalibrationInsights() {
  return useAsync<ApiCalibrationInsight[]>(async (signal) => {
    return qualityApi.listCalibrationInsights({ signal });
  }, []);
}
