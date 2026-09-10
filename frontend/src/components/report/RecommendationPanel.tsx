import { ArrowRight, FlaskConical } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ApiExperiment } from '@/api/types';
import { buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { experimentDetailPath } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { formatMoney } from '@/lib/format';

export interface RecommendationPanelProps {
  /** The Experiment Planner's top recommendation for this decision, if any. */
  experiment: ApiExperiment | null;
}

/** The conclusion of the report: the real, recommended experiment (if the
 * Experiment Planner produced one), never a fabricated verdict. */
export function RecommendationPanel({ experiment }: RecommendationPanelProps) {
  if (!experiment) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No experiment recommended yet"
        description="The Experiment Planner has not recommended a validation experiment for this decision, or the analysis has not reached this stage."
      />
    );
  }

  const facts = [
    experiment.estimated_cost !== null
      ? { label: 'Estimated cost', value: formatMoney(experiment.estimated_cost, experiment.currency === 'USD' ? 'USD' : 'INR') }
      : null,
    experiment.duration_days !== null ? { label: 'Duration', value: `${experiment.duration_days} days` } : null,
    experiment.expected_information_gain
      ? { label: 'Expected learning', value: experiment.expected_information_gain }
      : null,
  ].filter((fact): fact is { label: string; value: string } => fact !== null);

  return (
    <section className="overflow-hidden rounded-2xl border border-accent-line bg-panel-accent shadow-raised">
      <div className="p-6 md:p-7">
        <div className="flex items-center gap-2.5">
          <FlaskConical className="size-4 shrink-0 text-accent-ink" aria-hidden />
          <p className="eyebrow">Recommendation</p>
        </div>

        <h3 className="mt-4 text-headline text-ink">{experiment.title}</h3>

        <p className="mt-4 max-w-2xl text-body-lg text-ink-secondary">{experiment.hypothesis}</p>

        {facts.length > 0 ? (
          <dl className="mt-7 grid gap-4 sm:grid-cols-3">
            {facts.map((fact) => (
              <div key={fact.label} className="rounded-xl border border-hairline-strong bg-panel-inset px-5 py-4">
                <dt className="eyebrow">{fact.label}</dt>
                <dd className="numeric mt-2 text-card-title font-semibold text-ink">{fact.value}</dd>
              </div>
            ))}
          </dl>
        ) : null}

        <Link
          to={experimentDetailPath(experiment.id)}
          className={cn(buttonClasses({ variant: 'primary', size: 'lg' }), 'mt-7')}
        >
          View the experiment
          <ArrowRight className="size-4.5" aria-hidden />
        </Link>
      </div>
    </section>
  );
}
