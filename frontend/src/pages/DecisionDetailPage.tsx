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
  DecisionEvolutionPanel,
  DecisionMemoryPanel,
  DecisionSnapshot,
  HistoricalInsightsPanel,
  RecommendationPanel,
  ReportActions,
  ReportHeader,
  ReportSection,
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
import { useDecisionEvolution } from '@/hooks/useDecisionEvolution';
import { useDecisionMemory } from '@/hooks/useDecisionMemory';
import { useDecisionReportData } from '@/hooks/useDecisionReportData';
import { useHistoricalContext } from '@/hooks/useHistoricalContext';
import { usePatternsForDecision } from '@/hooks/usePatternsForDecision';
import { useValueOfInformation } from '@/hooks/useValueOfInformation';
import { buildAdaptiveCycleRows, buildAdaptiveLoopSummary } from '@/lib/buildAdaptiveLoop';
import { buildCrossDecisionPatternRows } from '@/lib/buildCrossDecisionPatterns';
import { buildDecisionEvolutionSummary } from '@/lib/buildDecisionEvolution';
import { buildDecisionMemorySummary, buildMemoryTimeline } from '@/lib/buildDecisionMemory';
import { buildHistoricalContext, EMPTY_HISTORICAL_SUMMARY } from '@/lib/buildHistoricalContext';
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
  const evolutionState = useDecisionEvolution(id);
  const patternsState = usePatternsForDecision(id);

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

  const assumptionStatementsById = Object.fromEntries(
    report.assumptions.map((assumption) => [assumption.id, assumption.statement]),
  );
  const experimentTitlesById = Object.fromEntries(
    report.experiments.map((experiment) => [experiment.id, experiment.title]),
  );

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
          title="Historical insights"
          description="Why REGRET connected these decisions: a deterministic similarity comparison against your own decision history - never another user's data, and never something that overrides this decision's own evidence or thresholds."
        >
          <HistoricalInsightsPanel
            summary={
              historicalContextState.data
                ? buildHistoricalContext(historicalContextState.data)
                : EMPTY_HISTORICAL_SUMMARY
            }
            isLoading={historicalContextState.isLoading}
          />
        </ReportSection>

        <ReportSection
          index="03"
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
          index="04"
          title="What should you test first?"
          description="Not simply the scariest risk - the uncertainty most worth resolving relative to the effort it takes to learn about it."
        >
          <ValueOfInformationPanel
            summary={buildValueOfInformation(voiState.data ?? null)}
            isLoading={voiState.isLoading}
          />
        </ReportSection>

        {patternsState.data && patternsState.data.length > 0 ? (
          <ReportSection
            index="05"
            title="What your past decisions teach"
            description="Recurring patterns from your OWN decision history - context for this decision, never a prediction about it."
          >
            <CrossDecisionPatternsPanel
              rows={buildCrossDecisionPatternRows(patternsState.data)}
              isLoading={patternsState.isLoading}
            />
          </ReportSection>
        ) : null}

        <ReportSection
          index="06"
          title="Decision validation"
          description="The closed loop: after a real experiment result comes in, REGRET ENGINE re-evaluates the decision and picks the next uncertainty worth testing - never repeating one that's already been conclusively resolved."
        >
          <AdaptiveLoopPanel
            summary={buildAdaptiveLoopSummary(adaptiveState.data ?? null)}
            isLoading={adaptiveState.isLoading}
            isAdvancing={adaptiveActions.isAdvancing}
            isStopping={adaptiveActions.isStopping}
            onAdvance={() => void handleAdvanceAdaptive()}
            onStop={adaptiveState.data ? () => void handleStopAdaptive() : undefined}
            errorMessage={adaptiveActions.error?.message ?? null}
          />
        </ReportSection>

        {adaptiveHistoryState.data && adaptiveHistoryState.data.length > 0 ? (
          <ReportSection
            index="07"
            title="Validation history"
            description="Every testing cycle this decision has gone through so far, in order."
          >
            <AdaptiveDecisionTimeline cycles={buildAdaptiveCycleRows(adaptiveHistoryState.data)} />
          </ReportSection>
        ) : null}

        <ReportSection
          index="08"
          title="Regret scenarios"
          description="Conditions under which this decision would be regretted."
        >
          <ScenarioCards scenarios={scenarios} />
        </ReportSection>

        <ReportSection
          index="09"
          title="Thresholds"
          description="The tipping points that decide whether this decision holds."
        >
          <ThresholdSection thresholds={thresholds} />
        </ReportSection>

        <ReportSection
          index="10"
          title="Assumptions"
          description="What the decision quietly depends on, and how well each one is backed by evidence."
        >
          <AssumptionsSection assumptions={assumptionRows} />
        </ReportSection>

        <ReportSection
          index="11"
          title="Challenges"
          description="The Devil's Advocate's strongest counter-arguments against this decision."
        >
          <ChallengeCards challenges={challenges} />
        </ReportSection>

        <Reveal>
          <RecommendationPanel experiment={recommendedExperiment} />
        </Reveal>

        <ReportSection
          index="12"
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
          index="13"
          title="Decision Evolution"
          description="Not a generic activity log - the causal chain from what we believed, through what we tested, to what actually changed and why."
        >
          <DecisionEvolutionPanel
            summary={buildDecisionEvolutionSummary(evolutionState.data ?? null)}
            isLoading={evolutionState.isLoading}
            assumptionStatementsById={assumptionStatementsById}
            experimentTitlesById={experimentTitlesById}
          />
        </ReportSection>

        <ReportSection index="14" title="Actions" className={cn('print:hidden')}>
          <ReportActions decisionId={decision.id} onEvidenceUploaded={reportState.refetch} />
        </ReportSection>
      </div>
    </PageContainer>
  );
}
