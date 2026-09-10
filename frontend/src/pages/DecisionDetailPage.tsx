import { FileSearch, Network, ScanSearch } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { DecisionNotFound } from '@/components/DecisionNotFound';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import {
  AssumptionsSection,
  ChallengeCards,
  DecisionSnapshot,
  RecommendationPanel,
  ReportActions,
  ReportHeader,
  ReportSection,
  ScenarioCards,
  ThresholdSection,
  UncertaintyCard,
} from '@/components/report';
import { buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonText } from '@/components/ui/Skeleton';
import { analysisPath, decisionGraphPath } from '@/data/navigation';
import { useDecisionById } from '@/hooks/useDecisionById';
import { useDecisionReportData } from '@/hooks/useDecisionReportData';
import { cn } from '@/lib/cn';
import {
  buildCriticalUncertainties,
  buildReportAssumptionRows,
  buildReportChallenges,
  buildReportScenarios,
  buildReportThresholds,
} from '@/lib/buildDecisionReport';

export function DecisionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const decisionState = useDecisionById(id);
  const reportState = useDecisionReportData(id);

  if (!id) return <DecisionNotFound id={id} />;

  if (decisionState.status === 'error') {
    if (decisionState.error?.message.toLowerCase().includes('not found')) {
      return <DecisionNotFound id={id} />;
    }
    return (
      <PageContainer eyebrow={`Decision ${id}`} title="Decision report">
        <ErrorState
          title="Unable to load this decision"
          description={decisionState.error?.message}
          detail={decisionState.error?.requestId ? `Request ID: ${decisionState.error.requestId}` : undefined}
        />
      </PageContainer>
    );
  }

  if (decisionState.isLoading || !decisionState.data) {
    return (
      <PageContainer eyebrow="Decision" title="Loading…">
        <SkeletonText lines={6} />
      </PageContainer>
    );
  }

  const decision = decisionState.data;

  if (reportState.status === 'error') {
    return (
      <PageContainer eyebrow={`Decision ${decision.id}`} title={decision.title} description={decision.description}>
        <ErrorState
          title="Unable to load the analysis for this decision"
          description={reportState.error?.message}
          detail={reportState.error?.requestId ? `Request ID: ${reportState.error.requestId}` : undefined}
          action={
            <button
              type="button"
              onClick={reportState.refetch}
              className="text-small font-medium text-accent-ink underline-offset-4 hover:underline"
            >
              Retry
            </button>
          }
        />
      </PageContainer>
    );
  }

  if (reportState.isLoading || !reportState.data) {
    return (
      <PageContainer eyebrow={`Decision ${decision.id}`} title={decision.title}>
        <SkeletonText lines={8} />
      </PageContainer>
    );
  }

  const report = reportState.data;
  const hasAnyAnalysis =
    report.assumptions.length > 0 ||
    report.blindspots.length > 0 ||
    report.thresholds.length > 0 ||
    report.regretScenarios.length > 0;

  if (!hasAnyAnalysis) {
    return (
      <PageContainer eyebrow={`Decision ${decision.id}`} title={decision.title} description={decision.description}>
        <EmptyState
          icon={FileSearch}
          title="No analysis yet"
          description="This decision has not been analysed yet. Run a stress test to surface its assumptions, blindspots and breaking points."
          action={
            <Link to={analysisPath(decision.id)} className={buttonClasses({ variant: 'primary', size: 'sm' })}>
              <ScanSearch className="size-4" aria-hidden />
              Run stress test
            </Link>
          }
        />
      </PageContainer>
    );
  }

  const uncertainties = buildCriticalUncertainties(report.assumptions, report.blindspots);
  const scenarios = buildReportScenarios(report.regretScenarios);
  const thresholds = buildReportThresholds(report.thresholds);
  const assumptionRows = buildReportAssumptionRows(report.assumptions);
  const challenges = buildReportChallenges(report.challenges);
  const recommendedExperiment =
    report.experiments.find((experiment) => experiment.status === 'recommended') ?? report.experiments[0] ?? null;

  const snapshot = [
    { label: 'Assumptions', value: String(report.assumptions.length) },
    { label: 'Blindspots', value: String(report.blindspots.length) },
    { label: 'Challenges', value: String(report.challenges.length) },
    { label: 'Regret scenarios', value: String(report.regretScenarios.length) },
    { label: 'Thresholds', value: String(report.thresholds.length) },
  ];

  return (
    <PageContainer>
      <div className="mx-auto max-w-5xl space-y-12 md:space-y-14">
        <ReportHeader decision={decision} />

        <ReportSection index="01" title="Decision snapshot">
          <DecisionSnapshot items={snapshot} />
        </ReportSection>

        <ReportSection
          index="02"
          title="What could break this decision?"
          description="Assumptions and blindspots, ranked by importance. Expand a card for detail."
          action={
            <Link to={decisionGraphPath(decision.id)} className={buttonClasses({ variant: 'secondary', size: 'sm' })}>
              <Network className="size-4" aria-hidden />
              Dependency graph
            </Link>
          }
        >
          <div className="space-y-4">
            {uncertainties.map((uncertainty, index) => (
              <UncertaintyCard key={uncertainty.id} uncertainty={uncertainty} defaultOpen={index === 0} />
            ))}
          </div>
        </ReportSection>

        <ReportSection
          index="03"
          title="Thresholds"
          description="The tipping points that decide whether this decision holds."
        >
          <ThresholdSection thresholds={thresholds} />
        </ReportSection>

        <ReportSection
          index="04"
          title="Regret scenarios"
          description="Conditions under which this decision would be regretted."
        >
          <ScenarioCards scenarios={scenarios} />
        </ReportSection>

        <ReportSection
          index="05"
          title="Assumptions"
          description="What the decision quietly depends on, and how well each one is backed by evidence."
        >
          <AssumptionsSection assumptions={assumptionRows} />
        </ReportSection>

        <ReportSection
          index="06"
          title="Challenges"
          description="The Devil's Advocate's strongest counter-arguments against this decision."
        >
          <ChallengeCards challenges={challenges} />
        </ReportSection>

        <Reveal>
          <RecommendationPanel experiment={recommendedExperiment} />
        </Reveal>

        <ReportSection index="07" title="Actions" className={cn('print:hidden')}>
          <ReportActions decisionId={decision.id} onEvidenceUploaded={reportState.refetch} />
        </ReportSection>
      </div>
    </PageContainer>
  );
}
