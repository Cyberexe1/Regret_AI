import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { FlaskConical } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import { ReportSection } from '@/components/report/ReportSection';
import {
  ExperimentDesign,
  ExperimentHistoryList,
  ExperimentResultForm,
  ExperimentResults,
  ReevaluationPanel,
  RecommendedExperimentCard,
} from '@/components/experiments';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonText } from '@/components/ui/Skeleton';
import { useExperimentDetail } from '@/hooks/useExperimentDetail';
import { useReevaluation } from '@/hooks/useReevaluation';
import { useWorkspaceExperiments } from '@/hooks/useWorkspaceExperiments';

function ExperimentDetailView({ experimentId }: { experimentId: string }) {
  const detailState = useExperimentDetail(experimentId);
  const [reevaluationId, setReevaluationId] = useState<string | null>(null);
  const reevaluationState = useReevaluation(detailState.data?.decision.id, reevaluationId ?? undefined);

  if (detailState.status === 'error') {
    return (
      <ErrorState
        title="Unable to load this experiment"
        description={detailState.error?.message}
        detail={detailState.error?.requestId ? `Request ID: ${detailState.error.requestId}` : undefined}
      />
    );
  }

  if (detailState.isLoading || !detailState.data) {
    return <SkeletonText lines={8} />;
  }

  const { experiment, decision, results } = detailState.data;
  const hasCompletedResult = results.length > 0 || experiment.status === 'completed';

  return (
    <div className="space-y-12 md:space-y-14">
      <Reveal>
        <RecommendedExperimentCard experiment={experiment} decision={decision} />
      </Reveal>

      <ReportSection
        index="01"
        title="Experiment design"
        description="What is being tested, what gets measured, and what counts as an answer either way."
      >
        <ExperimentDesign experiment={experiment} />
      </ReportSection>

      <ReportSection index="02" title="Results" description="What was actually observed.">
        <ExperimentResults results={results} />
      </ReportSection>

      {!hasCompletedResult ? (
        <ReportSection
          index="03"
          title="Submit a result"
          description="Record what happened when this experiment was run. This triggers deterministic re-evaluation of the target threshold and related assumptions."
        >
          <ExperimentResultForm
            experimentId={experiment.id}
            onSubmitted={(id) => {
              setReevaluationId(id);
              detailState.refetch();
            }}
          />
        </ReportSection>
      ) : null}

      {reevaluationId ? (
        <ReportSection index="04" title="Re-evaluation">
          {reevaluationState.status === 'error' ? (
            <ErrorState title="Unable to load the re-evaluation" description={reevaluationState.error?.message} />
          ) : reevaluationState.isLoading || !reevaluationState.data ? (
            <SkeletonText lines={6} />
          ) : (
            <ReevaluationPanel reevaluation={reevaluationState.data} />
          )}
        </ReportSection>
      ) : null}
    </div>
  );
}

function ExperimentListView() {
  const workspaceExperiments = useWorkspaceExperiments();

  if (workspaceExperiments.status === 'error') {
    return (
      <ErrorState
        title="Unable to load experiments"
        description={workspaceExperiments.error?.message}
        detail={workspaceExperiments.error?.requestId ? `Request ID: ${workspaceExperiments.error.requestId}` : undefined}
        action={
          <button
            type="button"
            onClick={workspaceExperiments.refetch}
            className="text-small font-medium text-accent-ink underline-offset-4 hover:underline"
          >
            Retry
          </button>
        }
      />
    );
  }

  if (workspaceExperiments.isLoading || !workspaceExperiments.data) {
    return <SkeletonText lines={8} />;
  }

  if (workspaceExperiments.data.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No experiments recommended yet"
        description="Run a stress test on a decision and the engine will propose the cheapest test that would change your mind."
      />
    );
  }

  return (
    <Reveal>
      <ExperimentHistoryList rows={workspaceExperiments.data} />
    </Reveal>
  );
}

export function ExperimentsPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <PageContainer
      eyebrow="Validation"
      title="Experiments"
      description="Reduce uncertainty before you make an expensive commitment."
    >
      <div className="mx-auto max-w-5xl">{id ? <ExperimentDetailView experimentId={id} /> : <ExperimentListView />}</div>
    </PageContainer>
  );
}
