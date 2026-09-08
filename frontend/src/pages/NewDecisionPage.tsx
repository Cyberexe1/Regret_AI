import { SquarePen } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PagePlaceholder } from '@/components/PagePlaceholder';
import { ROUTES } from '@/data/navigation';

export function NewDecisionPage() {
  return (
    <PageContainer
      eyebrow="Intake"
      title="Describe the decision"
      description="Stated in your own words, with the constraints that actually bind. The engine works from your framing, then challenges it."
      width="narrow"
    >
      <PagePlaceholder
        icon={SquarePen}
        route={ROUTES.newDecision}
        scope={[
          'Decision statement, domain, stakes and commit-by date',
          'Constraints and options the user has already ruled in or out',
          'Stated assumptions captured separately from inferred ones',
          'Hand-off into the analysis workspace once intake is complete',
        ]}
      />
    </PageContainer>
  );
}
