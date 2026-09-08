import { lazy, Suspense } from 'react';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import {
  ActivityTimeline,
  ChartCardFallback,
  DashboardHeader,
  MetricRow,
  OpenExperimentsCard,
  RecentDecisionsCard,
  UncertaintyCard,
} from '@/components/dashboard';

/**
 * The portfolio ring is the only consumer of Recharts on this page, so it loads
 * as its own chunk. That keeps the charting library out of the main bundle and
 * off every other route.
 */
const PortfolioCard = lazy(async () => {
  const module = await import('@/components/dashboard/PortfolioCard');
  return { default: module.PortfolioCard };
});

/**
 * Composition only. Each band is a dashboard component, and all figures come
 * from `data/dashboard.ts`.
 */
export function DashboardPage() {
  return (
    <PageContainer>
      <div className="space-y-8">
        <DashboardHeader />

        <MetricRow />

        {/* Decisions get the wider column; portfolio composition sits beside it. */}
        <div className="grid gap-5 lg:grid-cols-3">
          <Reveal className="lg:col-span-2">
            <RecentDecisionsCard />
          </Reveal>
          <Reveal delay={0.06}>
            <Suspense fallback={<ChartCardFallback />}>
              <PortfolioCard />
            </Suspense>
          </Reveal>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <Reveal className="lg:col-span-2">
            <OpenExperimentsCard />
          </Reveal>
          <Reveal delay={0.06}>
            <UncertaintyCard />
          </Reveal>
        </div>

        <Reveal>
          <ActivityTimeline />
        </Reveal>
      </div>
    </PageContainer>
  );
}
