import { ArrowLeft, SearchX } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import { buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ROUTES } from '@/data/navigation';

export interface DecisionNotFoundProps {
  id: string | undefined;
}

/** Shared by the report and graph routes, which resolve the same id. */
export function DecisionNotFound({ id }: DecisionNotFoundProps) {
  return (
    <PageContainer eyebrow="Decision" title="Decision not found" width="narrow">
      <EmptyState
        icon={SearchX}
        title="No decision matches this identifier"
        description={`The reference ${id ?? 'given'} is not in this workspace. It may have been removed, or the link may be out of date.`}
        action={
          <Link
            to={ROUTES.decisions}
            className={buttonClasses({ variant: 'secondary', size: 'sm' })}
          >
            <ArrowLeft className="size-4" aria-hidden />
            Back to decision history
          </Link>
        }
      />
    </PageContainer>
  );
}
