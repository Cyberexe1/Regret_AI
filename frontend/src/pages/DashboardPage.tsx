import { lazy, Suspense } from 'react';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import {
  ActivityTimeline,
  ChartCardFallback,
  DashboardHeader,
  HistoricalLessonsCard,
  MetricRow,
  OpenExperimentsCard,
  RecentDecisionLearningsCard,
  RecentDecisionsCard,
  UncertaintyCard,
} from '@/components/dashboard';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonText } from '@/components/ui/Skeleton';
import { useDashboard } from '@/hooks/useDashboard';
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

/**
 * Every figure on this page comes from `GET /decisions` (plus each
 * decision's experiments) via `useDashboard` - no static sample data
 * remains. A backend failure surfaces as a real error state, never a
 * silent fallback to fake numbers.
 */
export function DashboardPage() {
  const dashboard = useDashboard();

  if (dashboard.status === 'error') {
    return (
      <PageContainer>
        <DashboardHeader />
        <div className="mt-8">
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
      </PageContainer>
    );
  }

  if (dashboard.isLoading || !dashboard.data) {
    return (
      <PageContainer>
        <DashboardHeader />
        <div className="mt-8">
          <SkeletonText lines={8} />
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
      <div className="space-y-8">
        <DashboardHeader />

        <MetricRow metrics={metrics} />

        <div className="grid gap-5 lg:grid-cols-3">
          <Reveal className="lg:col-span-2">
            <RecentDecisionsCard rows={recentRows} />
          </Reveal>
          <Reveal delay={0.06}>
            <Suspense fallback={<ChartCardFallback />}>
              <PortfolioCard bands={portfolioBands} />
            </Suspense>
          </Reveal>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <Reveal className="lg:col-span-2">
            <OpenExperimentsCard rows={openExperimentRows} totalCount={totalOpenExperiments} />
          </Reveal>
          <Reveal delay={0.06}>
            <UncertaintyCard needsValidationCount={needsValidationCount} />
          </Reveal>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <Reveal className="lg:col-span-2">
            <ActivityTimeline events={activityEvents} />
          </Reveal>
          <Reveal delay={0.06}>
            <HistoricalLessonsCard summary={historicalLessons} />
          </Reveal>
        </div>

        <Reveal>
          <RecentDecisionLearningsCard rows={recentLearnings} />
        </Reveal>
      </div>
    </PageContainer>
  );
}
