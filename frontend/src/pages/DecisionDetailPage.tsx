import { ArrowLeft, ScanSearch } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import { Reveal } from '@/components/Reveal';
import {
  AssumptionsSection,
  DecisionSnapshot,
  RecommendationPanel,
  ReportActions,
  ReportHeader,
  ReportSection,
  ScenarioCards,
  ThresholdSection,
  UncertaintyCard,
} from '@/components/report';
import { Badge } from '@/components/ui/Badge';
import { buttonClasses } from '@/components/ui/Button';
import { Card, CardDescription, CardTitle } from '@/components/ui/Card';
import { findDecisionReport } from '@/data/decisionReport';
import { ROUTES } from '@/data/navigation';
import { useDecision } from '@/hooks/useDecisions';
import { cn } from '@/lib/cn';
import { domainLabel, reversibilityLabel, statusLabel } from '@/lib/labels';
import { regretIndexTone, reversibilityTone } from '@/lib/tone';

/** Shown when the id matches nothing in the workspace. */
function NotFound({ id }: { id: string | undefined }) {
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

export function DecisionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const decision = useDecision(id);

  if (!decision) return <NotFound id={id} />;

  const report = findDecisionReport(decision.id);

  // Only decisions with a completed stress test have a full report.
  if (!report) {
    const { analysis } = decision;

    return (
      <PageContainer
        eyebrow={`Decision ${decision.id}`}
        title={decision.title}
        description={decision.statement}
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

        <Card padding="lg" className="max-w-2xl space-y-4">
          <CardTitle>No full report yet</CardTitle>
          <CardDescription>
            {analysis
              ? 'This decision has an analysis on file but has not been through a full stress test, so there is no threshold model or recommended experiment to show.'
              : 'This decision has not been analysed yet. Run a stress test to surface its assumptions, failure conditions and breaking point.'}
          </CardDescription>
          <Link
            to={ROUTES.analysis}
            className={buttonClasses({ variant: 'primary', size: 'sm' })}
          >
            <ScanSearch className="size-4" aria-hidden />
            Run stress test
          </Link>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="mx-auto max-w-5xl space-y-12 md:space-y-14">
        <ReportHeader report={report} />

        <ReportSection index="01" title="Decision snapshot">
          <DecisionSnapshot items={report.snapshot} />
        </ReportSection>

        <ReportSection
          index="02"
          title="What could break this decision?"
          description="Ranked by how much each one moves the outcome. Expand a card for the evidence behind it."
        >
          <div className="space-y-4">
            {report.uncertainties.map((uncertainty, index) => (
              <UncertaintyCard
                key={uncertainty.id}
                uncertainty={uncertainty}
                defaultOpen={index === 0}
              />
            ))}
          </div>
        </ReportSection>

        <ReportSection
          index="03"
          title="The breaking point"
          description="The single value that decides whether this decision works."
        >
          <ThresholdSection report={report} />
        </ReportSection>

        <ReportSection
          index="04"
          title="Future scenarios"
          description="Three futures, with what would have to happen for each. Probabilities are illustrative."
        >
          <ScenarioCards scenarios={report.scenarios} />
        </ReportSection>

        <ReportSection
          index="05"
          title="Hidden assumptions"
          description="What the decision quietly depends on, and how well each one is backed."
        >
          <AssumptionsSection report={report} />
        </ReportSection>

        <Reveal>
          <RecommendationPanel recommendation={report.recommendation} />
        </Reveal>

        <ReportSection index="07" title="Actions" className={cn('print:hidden')}>
          <ReportActions />
        </ReportSection>
      </div>
    </PageContainer>
  );
}
