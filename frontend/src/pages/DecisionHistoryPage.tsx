import { History } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PagePlaceholder } from '@/components/PagePlaceholder';
import { ROUTES } from '@/data/navigation';

export function DecisionHistoryPage() {
  return (
    <PageContainer
      eyebrow="Archive"
      title="Decision history"
      description="Every decision the engine has analysed, including the ones abandoned before commitment."
    >
      <PagePlaceholder
        icon={History}
        route={ROUTES.decisions}
        scope={[
          'Filterable list by status, domain and stakes',
          'Regret index and reversibility shown per decision',
          'Outcome tracking for committed decisions against predicted scenarios',
          'Links through to each decision analysis',
        ]}
      />
    </PageContainer>
  );
}
