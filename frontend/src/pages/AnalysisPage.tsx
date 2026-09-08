import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  AgentPipeline,
  AnalysisHeader,
  AnalysisMetricsPanel,
  CompletionBanner,
  LiveFindings,
} from '@/components/analysis';
import { fallbackDecisionStatement } from '@/data/analysisAgents';
import { useAnalysisSimulation } from '@/hooks/useAnalysisSimulation';
import { readDecisionDraft } from '@/lib/decisionDraft';
import type { DecisionDraft } from '@/types';

/**
 * Live stress test. The pipeline is a local timed simulation: no engine is
 * called, and nothing beyond agent status and finished conclusions is shown.
 */
export function AnalysisPage() {
  const location = useLocation();
  const { progress, isComplete, agentStatuses, activeAgentId, findings, metrics } =
    useAnalysisSimulation();

  // Prefer the draft handed over by intake, then a stored one, then the sample.
  const decisionStatement = useMemo(() => {
    const handedOver = (location.state as { draft?: DecisionDraft } | null)?.draft?.decision?.trim();
    if (handedOver) return handedOver;

    const stored = readDecisionDraft()?.decision?.trim();
    if (stored) return stored;

    return fallbackDecisionStatement;
  }, [location.state]);

  return (
    <PageContainer>
      <div className="mx-auto max-w-6xl space-y-8">
        <AnalysisHeader decisionStatement={decisionStatement} isComplete={isComplete} />

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
          <div className="space-y-5">
            <AgentPipeline statuses={agentStatuses} activeAgentId={activeAgentId} />
            <LiveFindings findings={findings} isComplete={isComplete} />
          </div>

          <AnalysisMetricsPanel
            progress={progress}
            isComplete={isComplete}
            metrics={metrics}
          />
        </div>

        <CompletionBanner isComplete={isComplete} findingCount={findings.length} />
      </div>
    </PageContainer>
  );
}
