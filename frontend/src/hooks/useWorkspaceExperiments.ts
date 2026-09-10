import { decisionsApi, experimentsApi } from '@/api';
import type { ApiDecision, ApiExperiment } from '@/api/types';
import { useAsync } from './useAsync';

export interface WorkspaceExperimentRow {
  experiment: ApiExperiment;
  decision: ApiDecision | null;
}

/**
 * There is no global "list all experiments" endpoint on the backend -
 * experiments are only listable per-decision
 * (`GET /decisions/{id}/experiments`) or by their own id
 * (`GET /experiments/{id}`). This hook fans out across the workspace's
 * decisions (same pattern as `useDashboard`) to build one combined,
 * real list - never a fabricated one.
 */
export function useWorkspaceExperiments() {
  return useAsync<WorkspaceExperimentRow[]>(async (signal) => {
    const { items: decisions } = await decisionsApi.listDecisions({ limit: 50 }, { signal });

    const rows: WorkspaceExperimentRow[] = [];
    await Promise.all(
      decisions.map(async (decision) => {
        const experiments = await experimentsApi.listExperimentsForDecision(decision.id, { signal });
        for (const experiment of experiments) {
          rows.push({ experiment, decision });
        }
      }),
    );

    return rows.sort((a, b) => b.experiment.created_at.localeCompare(a.experiment.created_at));
  }, []);
}
