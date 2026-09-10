import { analysisApi, evidenceApi, experimentsApi } from '@/api';
import type {
  ApiAssumption,
  ApiBlindspot,
  ApiChallenge,
  ApiEvidence,
  ApiEvidenceFinding,
  ApiExperiment,
  ApiRegretScenario,
  ApiThreshold,
} from '@/api/types';
import { useAsync } from './useAsync';

export interface DecisionReportData {
  assumptions: ApiAssumption[];
  blindspots: ApiBlindspot[];
  evidence: ApiEvidence[];
  evidenceFindings: ApiEvidenceFinding[];
  challenges: ApiChallenge[];
  regretScenarios: ApiRegretScenario[];
  thresholds: ApiThreshold[];
  experiments: ApiExperiment[];
}

/**
 * Fetches every real analysis child-entity for a decision in parallel -
 * the data the Decision Report, Threshold visualization, and Decision
 * Graph all read from. All requests share one loading/error state since
 * these views only make sense once every piece is available together;
 * a partial failure surfaces as a single, clear error rather than
 * silently rendering half a report.
 */
export function useDecisionReportData(decisionId: string | undefined) {
  return useAsync<DecisionReportData>(
    async (signal) => {
      if (!decisionId) throw new Error('No decision id provided.');
      const options = { signal };
      const [
        assumptions,
        blindspots,
        evidence,
        evidenceFindings,
        challenges,
        regretScenarios,
        thresholds,
        experiments,
      ] = await Promise.all([
        analysisApi.listAssumptions(decisionId, options),
        analysisApi.listBlindspots(decisionId, options),
        evidenceApi.listEvidence(decisionId, options),
        analysisApi.listEvidenceFindings(decisionId, options),
        analysisApi.listChallenges(decisionId, options),
        analysisApi.listRegretScenarios(decisionId, options),
        analysisApi.listThresholds(decisionId, options),
        experimentsApi.listExperimentsForDecision(decisionId, options),
      ]);

      return {
        assumptions,
        blindspots,
        evidence,
        evidenceFindings,
        challenges,
        regretScenarios,
        thresholds,
        experiments,
      };
    },
    [decisionId],
  );
}
