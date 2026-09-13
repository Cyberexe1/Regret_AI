import { useParams } from 'react-router-dom';
import { DecisionNotFound } from '@/components/DecisionNotFound';
import { PageContainer } from '@/components/layout/PageContainer';
import { AgentPipeline, AnalysisHeader, AnalysisMetricsPanel, CompletionBanner } from '@/components/analysis';
import { HistoricalInsightsPanel, ReportSection } from '@/components/report';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAnalysisRun } from '@/hooks/useAnalysisRun';
import { useDecisionById } from '@/hooks/useDecisionById';
import { useHistoricalContext } from '@/hooks/useHistoricalContext';
import { buildHistoricalContext, EMPTY_HISTORICAL_SUMMARY } from '@/lib/buildHistoricalContext';

/**
 * Live stress test, driven entirely by the real backend pipeline. On
 * mount, ensures a decision has an analysis run (creating one if it
 * doesn't), then polls `GET /decisions/{id}/analysis/latest` every ~1.5s
 * until the run reaches a terminal status. No timing, progress, or
 * findings are simulated - every value shown is what the backend
 * actually reported.
 */
export function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const decisionState = useDecisionById(id);
  const analysis = useAnalysisRun(id);
  const historicalContext = useHistoricalContext(id);

  if (!id) return <DecisionNotFound id={id} />;

  if (decisionState.status === 'error') {
    return (
      <PageContainer eyebrow="Stress test" title="Analysis Workspace">
        <ErrorState
          title="Unable to load this decision"
          description={decisionState.error?.message}
          detail={decisionState.error?.requestId ? `Request ID: ${decisionState.error.requestId}` : undefined}
        />
      </PageContainer>
    );
  }

  if (analysis.triggerState === 'trigger-failed') {
    return (
      <PageContainer eyebrow="Stress test" title="Analysis Workspace">
        <ErrorState
          title="Could not start the analysis"
          description={analysis.triggerError?.message}
          detail={analysis.triggerError?.requestId ? `Request ID: ${analysis.triggerError.requestId}` : undefined}
        />
      </PageContainer>
    );
  }

  const decisionStatement =
    decisionState.data?.description ?? decisionState.data?.title ?? 'Loading your decision\u2026';

  return (
    <PageContainer>
      <div className="mx-auto max-w-6xl space-y-8">
        <AnalysisHeader decisionStatement={decisionStatement} isComplete={analysis.isComplete} />

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
          <div className="space-y-5">
            <AgentPipeline
              statuses={analysis.run?.stage_statuses ?? {}}
              activeAgentId={analysis.run?.current_stage ?? null}
            />
          </div>

          <AnalysisMetricsPanel run={analysis.run} isComplete={analysis.isComplete} />
        </div>

        {analysis.isComplete && !analysis.hasFailed ? (
          <ReportSection
            index="H"
            title="Historical Insights"
            description="Relevant context from your own past decisions - background only, never a substitute for this decision's own evidence and thresholds."
          >
            <HistoricalInsightsPanel
              summary={historicalContext.data ? buildHistoricalContext(historicalContext.data) : EMPTY_HISTORICAL_SUMMARY}
              isLoading={historicalContext.isLoading}
            />
          </ReportSection>
        ) : null}

        {analysis.isStalled ? (
          <ErrorState
            title="Lost connection to the backend"
            description={analysis.error?.message ?? 'Could not reach the analysis backend.'}
            detail={analysis.error?.requestId ? `Request ID: ${analysis.error.requestId}` : undefined}
            action={
              <button
                type="button"
                onClick={() => analysis.retry()}
                className="text-small font-medium text-accent-ink underline-offset-4 hover:underline"
              >
                Retry
              </button>
            }
          />
        ) : (
          <CompletionBanner
            isComplete={analysis.isComplete}
            hasFailed={analysis.hasFailed}
            decisionId={id}
            errorMessage={analysis.run?.error_message}
          />
        )}
      </div>
    </PageContainer>
  );
}
