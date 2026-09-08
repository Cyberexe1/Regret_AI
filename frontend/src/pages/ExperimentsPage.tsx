import { useMemo } from 'react';
import { FlaskConical } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import { ReportSection } from '@/components/report/ReportSection';
import {
  ExperimentDesign,
  ExperimentHistoryList,
  ExperimentProgressTracker,
  ExperimentResults,
  ExperimentVerdictCard,
  RecommendedExperimentCard,
} from '@/components/experiments';
import { EmptyState } from '@/components/ui/EmptyState';
import { decisions } from '@/data/decisions';
import { experiments, findExperiment } from '@/data/experiments';
import { findExperimentDetail, recommendedExperimentId } from '@/data/experimentProgram';
import { experimentPhase } from '@/lib/labels';

/** Running first, then proposed, then completed. Newest within each group. */
const PHASE_ORDER = { Running: 0, Proposed: 1, Completed: 2 } as const;

export function ExperimentsPage() {
  const experiment = findExperiment(recommendedExperimentId);
  const detail = findExperimentDetail(recommendedExperimentId);

  const decisionsById = useMemo(
    () => new Map(decisions.map((decision) => [decision.id, decision])),
    [],
  );

  const history = useMemo(
    () =>
      experiments.toSorted((a, b) => {
        const byPhase =
          PHASE_ORDER[experimentPhase(a.status)] - PHASE_ORDER[experimentPhase(b.status)];
        return byPhase !== 0 ? byPhase : b.createdAt.localeCompare(a.createdAt);
      }),
    [],
  );

  return (
    <PageContainer
      eyebrow="Validation"
      title="Experiments"
      description="Reduce uncertainty before you make an expensive commitment."
    >
      <div className="mx-auto max-w-5xl space-y-12 md:space-y-14">
        {experiment && detail ? (
          <>
            <Reveal>
              <RecommendedExperimentCard
                experiment={experiment}
                detail={detail}
                decision={decisionsById.get(experiment.decisionId)}
              />
            </Reveal>

            <ReportSection
              index="01"
              title="Experiment design"
              description="What is being tested, what gets measured, and what counts as an answer either way."
            >
              <ExperimentDesign experiment={experiment} detail={detail} />
            </ReportSection>

            <ReportSection
              index="02"
              title="Progress"
              description="Where the experiment is against its planned window."
            >
              <ExperimentProgressTracker detail={detail} />
            </ReportSection>

            <ReportSection
              index="03"
              title="Results so far"
              description="Interim readings. The experiment has not finished, so these can still move."
            >
              <ExperimentResults detail={detail} />
            </ReportSection>

            <Reveal>
              <ExperimentVerdictCard verdict={detail.verdict} />
            </Reveal>
          </>
        ) : (
          <EmptyState
            icon={FlaskConical}
            title="No experiment recommended yet"
            description="Run a stress test on a decision and the engine will propose the cheapest test that would change your mind."
          />
        )}

        <Reveal>
          <ExperimentHistoryList experiments={history} decisionsById={decisionsById} />
        </Reveal>
      </div>
    </PageContainer>
  );
}
