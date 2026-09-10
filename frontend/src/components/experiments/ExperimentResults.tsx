import { CheckCircle2 } from 'lucide-react';
import type { ApiExperimentResult } from '@/api/types';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatDate } from '@/lib/format';

export interface ExperimentResultsProps {
  results: ApiExperimentResult[];
}

const OUTCOME_TONE = {
  success: 'success',
  failure: 'danger',
  partial: 'warning',
  inconclusive: 'neutral',
} as const;

/** Real, previously-submitted experiment results - never a fabricated
 * progress bar or interim reading. */
export function ExperimentResults({ results }: ExperimentResultsProps) {
  if (results.length === 0) {
    return (
      <EmptyState
        size="inline"
        icon={CheckCircle2}
        title="No results submitted yet"
        description="Submit the observed outcome of this experiment once it has been run."
      />
    );
  }

  return (
    <div className="space-y-4">
      {results.map((result) => (
        <Card key={result.id}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Badge tone={OUTCOME_TONE[result.outcome]} size="sm" dot>
              {result.outcome}
            </Badge>
            <span className="text-micro text-ink-muted">{formatDate(result.completed_at)}</span>
          </div>

          <p className="mt-3 text-small text-ink">{result.summary}</p>

          {Object.keys(result.measured_values).length > 0 ? (
            <dl className="mt-4 grid gap-2 border-t border-hairline pt-3 sm:grid-cols-2">
              {Object.entries(result.measured_values).map(([key, value]) => (
                <div key={key} className="flex items-baseline justify-between gap-3">
                  <dt className="text-small text-ink-muted">{key}</dt>
                  <dd className="numeric text-small font-medium text-ink">{String(value)}</dd>
                </div>
              ))}
            </dl>
          ) : null}

          {result.observations.length > 0 ? (
            <ul className="mt-3 space-y-1.5 border-t border-hairline pt-3">
              {result.observations.map((observation) => (
                <li key={observation} className="text-small text-ink-secondary">
                  {observation}
                </li>
              ))}
            </ul>
          ) : null}
        </Card>
      ))}
    </div>
  );
}

