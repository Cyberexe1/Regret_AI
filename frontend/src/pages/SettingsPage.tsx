import { Settings } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PagePlaceholder } from '@/components/PagePlaceholder';
import { ROUTES } from '@/data/navigation';

export function SettingsPage() {
  return (
    <PageContainer
      eyebrow="Workspace"
      title="Settings"
      description="Workspace preferences, analysis defaults and how aggressively the engine challenges your framing."
      width="narrow"
    >
      <PagePlaceholder
        icon={Settings}
        route={ROUTES.settings}
        scope={[
          'Workspace name, members and roles',
          'Default regret horizons used in projections',
          'Challenge intensity: how hard the engine pushes on stated assumptions',
          'Data retention and export',
        ]}
      />
    </PageContainer>
  );
}
