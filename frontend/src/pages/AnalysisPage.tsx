import { ScanSearch } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PagePlaceholder } from '@/components/PagePlaceholder';
import { ROUTES } from '@/data/navigation';

export function AnalysisPage() {
  return (
    <PageContainer
      eyebrow="Engine"
      title="Analysis workspace"
      description="The working surface where a decision is pulled apart: assumptions, blind spots, failure conditions and projected regret."
    >
      <PagePlaceholder
        icon={ScanSearch}
        route={ROUTES.analysis}
        scope={[
          'Assumption ledger separating stated from hidden, scored by fragility',
          'Blind spots with the question that forces each one into the open',
          'Failure conditions with probability, horizon and early warning signal',
          'Regret trajectory comparing commit-now against run-an-experiment',
        ]}
      />
    </PageContainer>
  );
}
