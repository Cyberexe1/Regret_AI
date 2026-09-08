import { Check, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import type { Experiment, ExperimentDetail } from '@/types';

export interface ExperimentDesignProps {
  experiment: Experiment;
  detail: ExperimentDetail;
}

export function ExperimentDesign({ experiment, detail }: ExperimentDesignProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <p className="eyebrow">Hypothesis</p>
        <p className="mt-2.5 text-body text-ink">{experiment.hypothesis}</p>

        <p className="eyebrow mt-6">What to measure</p>
        <ul className="mt-3 grid gap-2.5 sm:grid-cols-2">
          {detail.measures.map((measure) => (
            <li key={measure} className="flex items-center gap-2.5 text-small text-ink-secondary">
              <span className="size-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
              {measure}
            </li>
          ))}
        </ul>

        <p className="eyebrow mt-6">Method</p>
        <p className="mt-2.5 text-small text-ink-secondary">{experiment.method}</p>
      </Card>

      <div className="space-y-4">
        <Card className="border-success-line/60 bg-success-soft/20">
          <div className="flex items-center gap-2">
            <Check className="size-4 shrink-0 text-success-ink" aria-hidden />
            <p className="eyebrow">Success</p>
          </div>
          <p className="numeric mt-2.5 text-card-title text-success-ink">
            {detail.successThreshold.replace('Repeat customer rate ', '')} repeat customer rate
          </p>
        </Card>

        <Card className="border-danger-line/60 bg-danger-soft/20">
          <div className="flex items-center gap-2">
            <X className="size-4 shrink-0 text-danger-ink" aria-hidden />
            <p className="eyebrow">Failure</p>
          </div>
          <p className="numeric mt-2.5 text-card-title text-danger-ink">
            {detail.failureThreshold.replace('Repeat customer rate ', '')} repeat customer rate
          </p>
        </Card>
      </div>
    </div>
  );
}
