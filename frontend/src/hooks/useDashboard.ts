import { decisionsApi, experimentsApi, historicalContextApi, memoryApi } from '@/api';
import type { ApiDecision, ApiExperiment, ApiHistoricalContext, ApiMemoryLearning } from '@/api/types';
import { useAsync } from './useAsync';

export interface DashboardData {
  decisions: ApiDecision[];
  /** Experiments for the decisions currently loaded, keyed by decision id. */
  experimentsByDecisionId: Map<string, ApiExperiment[]>;
  /** Decision Memory learnings for decisions that have at least one
   * experiment, keyed by decision id - see REGRET ENGINE 2.0's
   * "Recent Decision Learnings" dashboard card. */
  learningsByDecisionId: Map<string, ApiMemoryLearning[]>;
  /** Historical context (Decision Similarity & Historical Insight
   * Engine) for the workspace's most recent decisions, keyed by decision
   * id - bounded to `HISTORICAL_CONTEXT_DECISIONS_LIMIT` so the
   * dashboard never fans out into dozens of extra requests. Powers the
   * "Historical Lessons" card. */
  historicalContextByDecisionId: Map<string, ApiHistoricalContext>;
}

const RECENT_DECISIONS_LIMIT = 20;
/** Historical context is a heavier, deterministic-similarity computation
 * than a plain list read - bounded to a small handful of the workspace's
 * most recent decisions so the dashboard stays cheap, per the "do not
 * overload the dashboard" requirement. */
const HISTORICAL_CONTEXT_DECISIONS_LIMIT = 5;

/**
 * Loads the current user's most recent decisions and, for each, its
 * experiments - the real data every dashboard card derives its counts
 * from. Replaces the old static `data/dashboard.ts` module entirely; no
 * value shown on the dashboard is fabricated anymore.
 *
 * Bounded to the most recent `RECENT_DECISIONS_LIMIT` decisions (cursor
 * pagination's first page) - the dashboard is a snapshot, not the full
 * archive (that's Decision History, which paginates properly).
 */
export function useDashboard() {
  return useAsync<DashboardData>(async (signal) => {
    const { items: decisions } = await decisionsApi.listDecisions(
      { limit: RECENT_DECISIONS_LIMIT },
      { signal },
    );

    const experimentsByDecisionId = new Map<string, ApiExperiment[]>();
    const learningsByDecisionId = new Map<string, ApiMemoryLearning[]>();
    const historicalContextByDecisionId = new Map<string, ApiHistoricalContext>();
    await Promise.all(
      decisions.map(async (decision) => {
        try {
          const experiments = await experimentsApi.listExperimentsForDecision(decision.id, { signal });
          experimentsByDecisionId.set(decision.id, experiments);
        } catch {
          // A single decision's experiments failing to load must not blank
          // the whole dashboard - it simply shows zero experiments for that
          // decision rather than surfacing a page-level error.
          experimentsByDecisionId.set(decision.id, []);
        }
        try {
          const learnings = await memoryApi.listDecisionLearnings(decision.id, { signal });
          learningsByDecisionId.set(decision.id, learnings);
        } catch {
          // Same principle as experiments above - one decision's memory
          // failing to load must not blank the whole dashboard.
          learningsByDecisionId.set(decision.id, []);
        }
      }),
    );

    await Promise.all(
      decisions.slice(0, HISTORICAL_CONTEXT_DECISIONS_LIMIT).map(async (decision) => {
        try {
          const context = await historicalContextApi.getHistoricalContext(decision.id, { signal });
          historicalContextByDecisionId.set(decision.id, context);
        } catch {
          // Same principle - one decision's historical context failing to
          // load must not blank the whole dashboard.
        }
      }),
    );

    return { decisions, experimentsByDecisionId, learningsByDecisionId, historicalContextByDecisionId };
  }, []);
}
