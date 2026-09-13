import { FileSearch, Network, ScanSearch } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { DecisionNotFound } from '@/components/DecisionNotFound';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import {
  AdaptiveDecisionTimeline,
  AdaptiveLoopPanel,
  AssumptionsSection,
  ChallengeCards,
  CrossDecisionPatternsPanel,
  DecisionMemoryPanel,
  DecisionSnapshot,
  HistoricalInsightsPanel,
  QualityAssessmentPanel,
  RecommendationPanel,
  ReportActions,
  ReportHeader,
  ReportNav,
  ReportSection,
  ReportSummaryCard,
  ScenarioCards,
  ThresholdSection,
  UncertaintyCard,
  ValueOfInformationPanel,
} from '@/components/report';
import { buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonText } from '@/components/ui/Skeleton';
import { analysisPath, decisionGraphPath } from '@/data/navigation';
import { useAdaptiveActions } from '@/hooks/useAdaptiveActions';
import { useAdaptiveHistory } from '@/hooks/useAdaptiveHistory';
import { useAdaptiveState } from '@/hooks/useAdaptiveState';
import { useDecisionById } from '@/hooks/useDecisionById';
import { useDecisionMemory } from '@/hooks/useDecisionMemory';
import { useDecisionQuality } from '@/hooks/useDecisionQuality';
import { useDecisionReportData } from '@/hooks/useDecisionReportData';
import { useHistoricalContext } from '@/hooks/useHistoricalContext';
import { usePatternsForDecision } from '@/hooks/usePatternsForDecision';
import { useValueOfInformation } from '@/hooks/useValueOfInformation';
import { buildAdaptiveCycleRows, buildAdaptiveLoopSummary } from '@/lib/buildAdaptiveLoop';
import { buildCrossDecisionPatternRows } from '@/lib/buildCrossDecisionPatterns';
import { buildDecisionMemorySummary, buildMemoryTimeline } from '@/lib/buildDecisionMemory';
import { buildHistoricalContext, EMPTY_HISTORICAL_SUMMARY } from '@/lib/buildHistoricalContext';
import { buildQualityAssessmentSummary } from '@/lib/buildQualityAssessment';
import { buildValueOfInformation } from '@/lib/buildValueOfInformation';
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
  const memoryState = useDecisionMemory(id);
  const historicalContextState = useHistoricalContext(id);
  const voiState = useValueOfInformation(id);
  const adaptiveState = useAdaptiveState(id);
  const adaptiveHistoryState = useAdaptiveHistory(id);
  const adaptiveActions = useAdaptiveActions();
  const patternsState = usePatternsForDecision(id);
  const qualityState = useDecisionQuality(id);

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

  const handleAdvanceAdaptive = async () => {
    const response = await adaptiveActions.advance(decision.id);
    if (response) {
      adaptiveState.refetch();
      adaptiveHistoryState.refetch();
    }
  };

  const handleStopAdaptive = async () => {
    const response = await adaptiveActions.stop(decision.id);
    if (response) {
      adaptiveState.refetch();
      adaptiveHistoryState.refetch();
    }
  };

  const uncertainties = buildCriticalUncertainties(report.assumptions, report.blindspots);
  const scenarios = buildReportScenarios(report.regretScenarios);
  const thresholds = buildReportThresholds(report.thresholds);
  const assumptionRows = buildReportAssumptionRows(report.assumptions);
  const challenges = buildReportChallenges(report.challenges);
  const recommendedExperiment =
    report.experiments.find((experiment) => experiment.status === 'recommended') ?? report.experiments[0] ?? null;

  const adaptiveLoopSummary = buildAdaptiveLoopSummary(adaptiveState.data ?? null);
  const qualitySummary = buildQualityAssessmentSummary(qualityState.data ?? null);
  const topUncertainty = uncertainties[0] ?? null;
  const primaryThreshold = adaptiveLoopSummary.currentPrimaryThresholdId
    ? thresholds.find((threshold) => threshold.id === adaptiveLoopSummary.currentPrimaryThresholdId) ??
      thresholds[0] ??
      null
    : thresholds[0] ?? null;

  const snapshot = [
    { label: 'Assumptions', value: String(report.assumptions.length) },
    { label: 'Blindspots', value: String(report.blindspots.length) },
    { label: 'Challenges', value: String(report.challenges.length) },
    { label: 'Regret scenarios', value: String(report.regretScenarios.length) },
    { label: 'Thresholds', value: String(report.thresholds.length) },
  ];

  const navItems = [
    { id: 'report-snapshot', label: 'Decision snapshot' },
    { id: 'report-risks', label: 'What could break this decision?' },
    { id: 'report-voi', label: 'What to test first' },
    { id: 'report-history', label: 'Your history' },
    { id: 'report-validation', label: 'Validation' },
    { id: 'report-scenarios', label: 'Regret scenarios' },
    { id: 'report-thresholds', label: 'Thresholds' },
    { id: 'report-assumptions', label: 'Assumptions' },
    { id: 'report-challenges', label: 'Challenges' },
    { id: 'report-memory', label: 'Decision Memory' },
    { id: 'report-quality', label: 'Analysis Quality' },
  ];

  return (
    <PageContainer>
      <div className="mx-auto max-w-6xl">
        <ReportHeader decision={decision} />

        <div className="mt-8">
          <ReportSummaryCard
            topUncertainty={topUncertainty}
            primaryThreshold={primaryThreshold}
            recommendedExperiment={recommendedExperiment}
            quality={qualitySummary}
          />
        </div>

        <div className="mt-10 grid gap-8 lg:grid-cols-[minmax(0,1fr)_14rem] lg:items-start">
          <div className="min-w-0 space-y-12 md:space-y-14">
            <ReportSection title="Actions" className={cn('print:hidden')}>
              <ReportActions decisionId={decision.id} onEvidenceUploaded={reportState.refetch} />
            </ReportSection>

            <ReportSection id="report-snapshot" index="01" title="Decision snapshot" defaultOpen>
              <DecisionSnapshot items={snapshot} />
            </ReportSection>

            <ReportSection
              id="report-risks"
              index="02"
              title="What could break this decision?"
              description="Assumptions and blindspots, ranked by importance. Expand a card for detail."
              action={
                <Link
                  to={decisionGraphPath(decision.id)}
                  className={buttonClasses({ variant: 'secondary', size: 'sm' })}
                >
                  <Network className="size-4" aria-hidden />
                  Dependency graph
                </Link>
              }
              defaultOpen
            >
              <div className="space-y-4">
                {uncertainties.map((uncertainty, index) => (
                  <UncertaintyCard key={uncertainty.id} uncertainty={uncertainty} defaultOpen={index === 0} />
                ))}
              </div>
            </ReportSection>

            <ReportSection
              id="report-voi"
              index="03"
              title="What should you test first?"
              description="Not simply the scariest risk - the uncertainty most worth resolving relative to the effort it takes to learn about it."
            >
              <ValueOfInformationPanel
                summary={buildValueOfInformation(voiState.data ?? null)}
                isLoading={voiState.isLoading}
              />
            </ReportSection>

            <ReportSection
              id="report-history"
              index="04"
              title="Your history"
              description="What REGRET connected from your own past decisions - background context, never something that overrides this decision's own evidence or thresholds."
            >
              <div className="space-y-8">
                <HistoricalInsightsPanel
                  summary={
                    historicalContextState.data
                      ? buildHistoricalContext(historicalContextState.data)
                      : EMPTY_HISTORICAL_SUMMARY
                  }
                  isLoading={historicalContextState.isLoading}
                />

                {patternsState.data && patternsState.data.length > 0 ? (
                  <div className="border-t border-hairline pt-6">
                    <p className="eyebrow">Recurring patterns across your decisions</p>
                    <div className="mt-4">
                      <CrossDecisionPatternsPanel
                        rows={buildCrossDecisionPatternRows(patternsState.data)}
                        isLoading={patternsState.isLoading}
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            </ReportSection>

            <ReportSection
              id="report-validation"
              index="05"
              title="Validation"
              description="The closed loop: after a real experiment result comes in, REGRET ENGINE re-evaluates the decision and picks the next uncertainty worth testing - never repeating one that's already been conclusively resolved."
            >
              <div className="space-y-8">
                <AdaptiveLoopPanel
                  summary={adaptiveLoopSummary}
                  isLoading={adaptiveState.isLoading}
                  isAdvancing={adaptiveActions.isAdvancing}
                  isStopping={adaptiveActions.isStopping}
                  onAdvance={() => void handleAdvanceAdaptive()}
                  onStop={adaptiveState.data ? () => void handleStopAdaptive() : undefined}
                  errorMessage={adaptiveActions.error?.message ?? null}
                />

                {adaptiveHistoryState.data && adaptiveHistoryState.data.length > 0 ? (
                  <div className="border-t border-hairline pt-6">
                    <p className="eyebrow">Validation history</p>
                    <div className="mt-4">
                      <AdaptiveDecisionTimeline cycles={buildAdaptiveCycleRows(adaptiveHistoryState.data)} />
                    </div>
                  </div>
                ) : null}
              </div>
            </ReportSection>

            <ReportSection
              id="report-scenarios"
              index="06"
              title="Regret scenarios"
              description="Conditions under which this decision would be regretted."
            >
              <ScenarioCards scenarios={scenarios} />
            </ReportSection>

            <ReportSection
              id="report-thresholds"
              index="07"
              title="Thresholds"
              description="The tipping points that decide whether this decision holds."
            >
              <ThresholdSection thresholds={thresholds} />
            </ReportSection>

            <ReportSection
              id="report-assumptions"
              index="08"
              title="Assumptions"
              description="What the decision quietly depends on, and how well each one is backed by evidence."
            >
              <AssumptionsSection assumptions={assumptionRows} />
            </ReportSection>

            <ReportSection
              id="report-challenges"
              index="09"
              title="Challenges"
              description="The Devil's Advocate's strongest counter-arguments against this decision."
            >
              <ChallengeCards challenges={challenges} />
            </ReportSection>

            <Reveal>
              <RecommendationPanel experiment={recommendedExperiment} />
            </Reveal>

            <ReportSection
              id="report-memory"
              index="10"
              title="Decision Memory"
              description="What we believed, what we tested, what actually happened, and what changed as a result."
            >
              {memoryState.isLoading || !memoryState.data ? (
                <SkeletonText lines={4} />
              ) : (
                <DecisionMemoryPanel
                  summary={buildDecisionMemorySummary(memoryState.data)}
                  timeline={buildMemoryTimeline(decision.created_at, memoryState.data)}
                />
              )}
            </ReportSection>

            <ReportSection
              id="report-quality"
              index="11"
              title="Analysis Quality"
              description="How strong is this analysis? A deterministic, inspectable self-assessment of how well-grounded the current evidence, assumptions, and thresholds are - not a re-judgment of whether the decision itself is wise."
            >
              <QualityAssessmentPanel summary={qualitySummary} isLoading={qualityState.isLoading} />
            </ReportSection>
          </div>

          <ReportNav items={navItems} />
        </div>
      </div>
    </PageContainer>
  );
}
