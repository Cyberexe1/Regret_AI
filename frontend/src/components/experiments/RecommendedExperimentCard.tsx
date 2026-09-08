import { ArrowUpRight, FlaskConical } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { decisionPath } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { formatMoney } from '@/lib/format';
import { riskLabel, riskTone, toneText } from '@/lib/tone';
import type { Decision, Experiment, ExperimentDetail } from '@/types';

export interface RecommendedExperimentCardProps {
  experiment: Experiment;
  detail: ExperimentDetail;
  decision: Decision | undefined;
}

function Fact({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-hairline-strong bg-panel-inset px-4 py-3.5">
      <p className="eyebrow">{label}</p>
      <p className={cn('numeric mt-2 text-card-title font-semibold', tone ?? 'text-ink')}>
        {value}
      </p>
    </div>
  );
}

/** The one experiment the engine is putting forward, given prominence. */
export function RecommendedExperimentCard({
  experiment,
  detail,
  decision,
}: RecommendedExperimentCardProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-accent-line bg-panel-accent shadow-raised">
      <div className="p-6 md:p-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <FlaskConical className="size-4 shrink-0 text-accent-ink" aria-hidden />
            <p className="eyebrow">Recommended experiment</p>
          </div>
          <Badge tone="info" size="sm" dot>
            Running
          </Badge>
        </div>

        <h2 className="mt-4 text-headline text-ink">
          {experiment.title}
        </h2>

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

        <div className="mt-6 rounded-xl border border-hairline-strong bg-panel-inset px-5 py-4">
          <p className="eyebrow">The question</p>
          <p className="mt-2 text-section-title text-ink">{detail.question}</p>
        </div>

        <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Fact label="Success threshold" value={detail.successThreshold} />
          <Fact
            label="Estimated cost"
            value={formatMoney(experiment.cost.amount, experiment.cost.currency)}
          />
          <Fact label="Duration" value={`${detail.durationDays} days`} />
          <Fact
            label="Expected learning"
            value={riskLabel[detail.expectedLearning]}
            tone={toneText[riskTone[detail.expectedLearning]]}
          />
        </dl>
      </div>
    </section>
  );
}
