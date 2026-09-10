import { decisionsApi, experimentsApi } from '@/api';
import type { ApiDecision, ApiExperiment, ApiExperimentResult } from '@/api/types';
import { useAsync } from './useAsync';

export interface ExperimentDetailData {
  experiment: ApiExperiment;
  decision: ApiDecision;
  results: ApiExperimentResult[];
}

export function useExperimentDetail(experimentId: string | undefined) {
  return useAsync<ExperimentDetailData>(
    async (signal) => {
      if (!experimentId) throw new Error('No experiment id provided.');
      const experiment = await experimentsApi.getExperiment(experimentId, { signal });
      const [decision, results] = await Promise.all([
        decisionsApi.getDecision(experiment.decision_id, { signal }),
        experimentsApi.listExperimentResults(experimentId, { signal }),
      ]);
      return { experiment, decision, results };
    },
    [experimentId],
  );
}
