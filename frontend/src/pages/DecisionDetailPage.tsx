import { ArrowLeft, ScanSearch } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import { PagePlaceholder } from '@/components/PagePlaceholder';
import { Badge } from '@/components/ui/Badge';
import { buttonClasses } from '@/components/ui/Button';
import { Card, CardDescription, CardTitle } from '@/components/ui/Card';
import { ROUTES } from '@/data/navigation';
import { useDecision } from '@/hooks/useDecisions';
import { cn } from '@/lib/cn';
import { domainLabel, reversibilityLabel, statusLabel } from '@/lib/labels';
import { regretIndexTone, reversibilityTone } from '@/lib/tone';

export function DecisionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const decision = useDecision(id);

  if (!decision) {
    return (
      <PageContainer eyebrow="Decision" title="Decision not found" width="narrow">
        <Card padding="lg" className="space-y-4">
          <CardTitle>No decision matches this identifier</CardTitle>
          <CardDescription>
            The reference <span className="numeric text-ink">{id}</span> is not in this workspace. It
            may have been removed, or the link may be out of date.
          </CardDescription>
          <Link to={ROUTES.decisions} className={buttonClasses({ variant: 'secondary', size: 'sm' })}>
            <ArrowLeft className="size-4" aria-hidden />
            Back to decision history
          </Link>
        </Card>
      </PageContainer>
    );
  }

  const { analysis } = decision;

  return (
    <PageContainer
      eyebrow={`Decision ${decision.id}`}
      title={decision.title}
      description={decision.statement}
      actions={
        <Link
          to={ROUTES.analysis}
          className={cn(buttonClasses({ variant: 'secondary', size: 'sm' }))}
        >
          <ScanSearch className="size-4" aria-hidden />
          Open analysis workspace
        </Link>
      }
    >
      <div className="mb-6 flex flex-wrap items-center gap-2">
        <Badge tone="neutral" dot>
          {statusLabel[decision.status]}
        </Badge>
        <Badge variant="outline">{domainLabel[decision.domain]}</Badge>
        {analysis ? (
          <>
            <Badge tone={reversibilityTone[analysis.reversibility]}>
              {reversibilityLabel[analysis.reversibility]}
            </Badge>
            <Badge tone={regretIndexTone(analysis.regretIndex)}>
              Regret index <span className="numeric ml-1">{analysis.regretIndex}</span>
            </Badge>
          </>
        ) : (
          <Badge tone="info">Not yet analysed</Badge>
        )}
      </div>

      <PagePlaceholder
        icon={ScanSearch}
        route={ROUTES.decisionDetail}
        scope={[
          'Verdict summary with the reasoning that produced it',
          'Assumption ledger, blind spots and failure conditions for this decision',
          'Regret scenarios across the 6-month to 5-year horizons',
          'The recommended cheapest experiment, with its success criteria',
        ]}
      />

      <div className="mt-6">
        <Link to={ROUTES.decisions} className={buttonClasses({ variant: 'ghost', size: 'sm' })}>
          <ArrowLeft className="size-4" aria-hidden />
          Back to decision history
        </Link>
      </div>
    </PageContainer>
  );
}
