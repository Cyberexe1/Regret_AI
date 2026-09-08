import { FlaskConical } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PagePlaceholder } from '@/components/PagePlaceholder';
import { ROUTES } from '@/data/navigation';

export function ExperimentsPage() {
  return (
    <PageContainer
      eyebrow="Validation"
      title="Experiments"
      description="The cheapest tests available before committing, ranked by how much uncertainty each one removes."
    >
      <PagePlaceholder
        icon={FlaskConical}
        route={ROUTES.experiments}
        scope={[
          'Experiments ranked by information gain against cost',
          'Which assumption each experiment attacks',
          'Success criteria recorded before the experiment starts',
          'Findings written back onto the decision that prompted them',
        ]}
      />
    </PageContainer>
  );
}
