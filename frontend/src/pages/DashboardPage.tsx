import { LayoutDashboard } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PagePlaceholder } from '@/components/PagePlaceholder';
import { ROUTES } from '@/data/navigation';

export function DashboardPage() {
  return (
    <PageContainer
      eyebrow="Overview"
      title="Decision portfolio"
      description="Where regret exposure is concentrated across every decision currently in the engine."
    >
      <PagePlaceholder
        icon={LayoutDashboard}
        route={ROUTES.dashboard}
        scope={[
          'Portfolio regret index with trend against the previous period',
          'Decisions ranked by irreversibility and time remaining to commit',
          'Assumptions that are fragile and still untested',
          'Experiments in flight and the belief they are expected to move',
        ]}
      />
    </PageContainer>
  );
}
