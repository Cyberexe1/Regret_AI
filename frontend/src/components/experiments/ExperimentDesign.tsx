import { Check, X } from 'lucide-react';
import type { ApiExperiment } from '@/api/types';
import { Card } from '@/components/ui/Card';
import { formatMoney } from '@/lib/format';

export interface ExperimentDesignProps {
  experiment: ApiExperiment;
}

export function ExperimentDesign({ experiment }: ExperimentDesignProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <p className="eyebrow">Hypothesis</p>
        <p className="mt-2.5 text-body text-ink">{experiment.hypothesis}</p>

        {experiment.evidence_to_collect.length > 0 ? (
          <>
            <p className="eyebrow mt-6">What to measure</p>
            <ul className="mt-3 grid gap-2.5 sm:grid-cols-2">
              {experiment.evidence_to_collect.map((measure) => (
                <li key={measure} className="flex items-center gap-2.5 text-small text-ink-secondary">
                  <span className="size-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
                  {measure}
                </li>
              ))}
            </ul>
          </>
        ) : null}

        {experiment.steps.length > 0 ? (
          <>
            <p className="eyebrow mt-6">Method</p>
            <ol className="mt-3 space-y-2">
              {experiment.steps.map((step, index) => (
                <li key={step} className="flex gap-2.5 text-small text-ink-secondary">
                  <span className="numeric shrink-0 text-ink-muted">{index + 1}.</span>
                  {step}
                </li>
              ))}
            </ol>
          </>
        ) : null}

        {experiment.decision_rule ? (
          <>
            <p className="eyebrow mt-6">Decision rule</p>
            <p className="mt-2.5 text-small text-ink-secondary">{experiment.decision_rule}</p>
          </>
        ) : null}
      </Card>

      <div className="space-y-4">
        {experiment.success_criteria.length > 0 ? (
          <Card className="border-success-line bg-panel-success">
            <div className="flex items-center gap-2">
              <Check className="size-4 shrink-0 text-success-ink" aria-hidden />
              <p className="eyebrow">Success criteria</p>
            </div>
            <ul className="mt-2.5 space-y-1.5">
              {experiment.success_criteria.map((criterion) => (
                <li key={criterion} className="text-small text-success-ink">
                  {criterion}
                </li>
              ))}
            </ul>
          </Card>
        ) : null}

        {experiment.failure_criteria.length > 0 ? (
          <Card className="border-danger-line bg-panel-danger">
            <div className="flex items-center gap-2">
              <X className="size-4 shrink-0 text-danger-ink" aria-hidden />
              <p className="eyebrow">Failure criteria</p>
            </div>
            <ul className="mt-2.5 space-y-1.5">
              {experiment.failure_criteria.map((criterion) => (
                <li key={criterion} className="text-small text-danger-ink">
                  {criterion}
                </li>
              ))}
            </ul>
          </Card>
        ) : null}

        {experiment.estimated_cost !== null || experiment.duration_days !== null ? (
          <Card>
            {experiment.estimated_cost !== null ? (
              <p className="text-small text-ink-secondary">
                Estimated cost:{' '}
                <span className="numeric font-medium text-ink">
                  {formatMoney(experiment.estimated_cost, experiment.currency === 'USD' ? 'USD' : 'INR')}
                </span>
              </p>
            ) : null}
            {experiment.duration_days !== null ? (
              <p className="mt-1.5 text-small text-ink-secondary">
                Duration: <span className="numeric font-medium text-ink">{experiment.duration_days} days</span>
              </p>
            ) : null}
          </Card>
        ) : null}
      </div>
    </div>
  );
}
