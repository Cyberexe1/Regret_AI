import { lazy, Suspense } from 'react';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import {
  ActivityTimeline,
  CalibrationInsightsCard,
  ChartCardFallback,
  CrossDecisionPatternsCard,
  DashboardHeader,
  HistoricalLessonsCard,
  MetricRow,
  OpenExperimentsCard,
  RecentDecisionLearningsCard,
  RecentDecisionsCard,
  UncertaintyCard,
} from '@/components/dashboard';
import { Card } from '@/components/ui/Card';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useCalibrationInsights } from '@/hooks/useCalibrationInsights';
import { useCrossDecisionPatterns } from '@/hooks/useCrossDecisionPatterns';
import { useDashboard } from '@/hooks/useDashboard';
import { buildCalibrationInsightRows } from '@/lib/buildQualityAssessment';
import { buildCrossDecisionPatternRows } from '@/lib/buildCrossDecisionPatterns';
import {
  buildActivityEvents,
  buildDashboardMetrics,
  buildHistoricalLessonsSummary,
  buildOpenExperimentRows,
  buildPortfolioBands,
  buildRecentDecisionRows,
  buildRecentLearnings,
} from '@/lib/buildDashboard';

const PortfolioCard = lazy(async () => {
  const module = await import('@/components/dashboard/PortfolioCard');
  return { default: module.PortfolioCard };
});

function ListCardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <Card padding="none" className="min-w-0 overflow-hidden">
      <div className="border-b border-hairline px-4 py-4 sm:px-5 md:px-6">
        <Skeleton className="h-4 w-36 max-w-full" />
        <Skeleton className="mt-2 h-3 w-52 max-w-full" />
      </div>
      <div className="divide-y divide-hairline">
        {Array.from({ length: rows }, (_, index) => (
          <div key={index} className="space-y-3 px-4 py-4 sm:px-5">
            <Skeleton className="h-3.5 w-3/4" />
            <div className="flex min-w-0 items-center gap-3">
              <Skeleton className="h-3 min-w-0 flex-1" />
              <Skeleton className="h-5 w-20 shrink-0" />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function PanelCardSkeleton() {
  return (
    <Card className="min-w-0">
      <Skeleton className="h-4 w-32 max-w-full" />
      <Skeleton className="mt-3 h-3 w-full" />
      <Skeleton className="mt-2 h-3 w-4/5" />
      <Skeleton shape="block" className="mt-6 h-9 w-28 max-w-full" />
    </Card>
  );
}

function DashboardLoading() {
  return (
    <div className="min-w-0 space-y-5 sm:space-y-6" role="status" aria-label="Loading dashboard" aria-busy>
      <div className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} shape="block" className="h-28 min-w-0" />
        ))}
      </div>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
        <ListCardSkeleton />
        <ChartCardFallback />
      </div>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
        <ListCardSkeleton rows={2} />
        <PanelCardSkeleton />
      </div>
    </div>
  );
}

/**
 * Every figure on this page comes from `GET /decisions` (plus each
 * decision's experiments) via `useDashboard` - no static sample data
 * remains. A backend failure surfaces as a real error state, never a
 * silent fallback to fake numbers.
 */
export function DashboardPage() {
  const dashboard = useDashboard();
  const crossDecisionPatterns = useCrossDecisionPatterns();
  const calibrationInsights = useCalibrationInsights();

  if (dashboard.status === 'error') {
    return (
      <PageContainer>
        <div className="min-w-0">
          <DashboardHeader />
          <div className="mt-6 sm:mt-8">
            <ErrorState
              title="Unable to load your dashboard"
              description={dashboard.error?.message}
              detail={dashboard.error?.requestId ? `Request ID: ${dashboard.error.requestId}` : undefined}
              action={
                <button
                  type="button"
                  onClick={dashboard.refetch}
                  className="text-small font-medium text-accent-ink underline-offset-4 hover:underline"
                >
                  Retry
                </button>
              }
            />
          </div>
        </div>
      </PageContainer>
    );
  }

  if (dashboard.isLoading || !dashboard.data) {
    return (
      <PageContainer>
        <div className="min-w-0 space-y-6 sm:space-y-8">
          <DashboardHeader />
          <DashboardLoading />
        </div>
      </PageContainer>
    );
  }

  const data = dashboard.data;
  const metrics = buildDashboardMetrics(data);
  const recentRows = buildRecentDecisionRows(data);
  const portfolioBands = buildPortfolioBands(data);
  const openExperimentRows = buildOpenExperimentRows(data);
  const totalOpenExperiments = [...data.experimentsByDecisionId.values()]
    .flat()
    .filter((e) => e.status === 'recommended' || e.status === 'active' || e.status === 'planned').length;
  const activityEvents = buildActivityEvents(data);
  const recentLearnings = buildRecentLearnings(data);
  const historicalLessons = buildHistoricalLessonsSummary(data);
  const needsValidationCount = data.decisions.filter((d) => d.status === 'needs_validation').length;

  return (
    <PageContainer>
      <div className="min-w-0 space-y-6 sm:space-y-8">
        <DashboardHeader />

        <MetricRow metrics={metrics} />

        <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
          <Reveal className="min-w-0">
            <RecentDecisionsCard rows={recentRows} />
          </Reveal>
          <Reveal className="min-w-0" delay={0.06}>
            <Suspense fallback={<ChartCardFallback />}>
              <PortfolioCard bands={portfolioBands} />
            </Suspense>
          </Reveal>
        </div>

        <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
          <Reveal className="min-w-0">
            <OpenExperimentsCard rows={openExperimentRows} totalCount={totalOpenExperiments} />
          </Reveal>
          <Reveal className="min-w-0" delay={0.06}>
            <UncertaintyCard needsValidationCount={needsValidationCount} />
          </Reveal>
        </div>

        <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
          <Reveal className="min-w-0">
            <ActivityTimeline events={activityEvents} />
          </Reveal>
          <Reveal className="min-w-0" delay={0.06}>
            <HistoricalLessonsCard summary={historicalLessons} />
          </Reveal>
        </div>

        <div className="grid min-w-0 gap-5 xl:grid-cols-2">
          <Reveal className="min-w-0">
            <CrossDecisionPatternsCard
              rows={buildCrossDecisionPatternRows(crossDecisionPatterns.data ?? [])}
              isLoading={crossDecisionPatterns.isLoading}
            />
          </Reveal>
          <Reveal className="min-w-0" delay={0.06}>
            <CalibrationInsightsCard
              rows={buildCalibrationInsightRows(calibrationInsights.data ?? [])}
              isLoading={calibrationInsights.isLoading}
            />
          </Reveal>
        </div>

        <Reveal className="min-w-0">
          <RecentDecisionLearningsCard rows={recentLearnings} />
        </Reveal>
      </div>
    </PageContainer>
  );
}
