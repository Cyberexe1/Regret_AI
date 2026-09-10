import { ArrowUpRight, FlaskConical } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ApiDecision, ApiExperiment } from '@/api/types';
import { Badge } from '@/components/ui/Badge';
import { decisionPath } from '@/data/navigation';
import { formatMoney } from '@/lib/format';
import { experimentStatusLabel } from '@/lib/labels';
import { experimentStatusTone } from '@/lib/reportModel';

export interface RecommendedExperimentCardProps {
  experiment: ApiExperiment;
  decision: ApiDecision | null;
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-hairline-strong bg-panel-inset px-4 py-3.5">
      <p className="eyebrow">{label}</p>
      <p className="numeric mt-2 text-card-title font-semibold text-ink">{value}</p>
    </div>
  );
}

export function RecommendedExperimentCard({ experiment, decision }: RecommendedExperimentCardProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-accent-line bg-panel-accent shadow-raised">
      <div className="p-6 md:p-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <FlaskConical className="size-4 shrink-0 text-accent-ink" aria-hidden />
            <p className="eyebrow">Experiment</p>
          </div>
          <Badge tone={experimentStatusTone(experiment.status)} size="sm" dot>
            {experimentStatusLabel[experiment.status]}
          </Badge>
        </div>

        <h2 className="mt-4 text-headline text-ink">{experiment.title}</h2>

        {decision ? (
          <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-small text-ink-secondary">
            Linked decision
            <Link
              to={decisionPath(decision.id)}
              className="inline-flex items-center gap-1 font-medium text-accent-ink transition-colors hover:text-ink"
            >
              {decision.title}
              <ArrowUpRight className="size-3.5" aria-hidden />
            </Link>
          </p>
        ) : null}

        {experiment.objective ? (
          <div className="mt-6 rounded-xl border border-hairline-strong bg-panel-inset px-5 py-4">
            <p className="eyebrow">Objective</p>
            <p className="mt-2 text-section-title text-ink">{experiment.objective}</p>
          </div>
        ) : null}

        <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {experiment.estimated_cost !== null ? (
            <Fact
              label="Estimated cost"
              value={formatMoney(experiment.estimated_cost, experiment.currency === 'USD' ? 'USD' : 'INR')}
            />
          ) : null}
          {experiment.duration_days !== null ? <Fact label="Duration" value={`${experiment.duration_days} days`} /> : null}
          {experiment.variable_to_test ? <Fact label="Variable tested" value={experiment.variable_to_test} /> : null}
          {experiment.expected_information_gain ? (
            <Fact label="Expected learning" value={experiment.expected_information_gain} />
          ) : null}
        </dl>
      </div>
    </section>
  );
}
