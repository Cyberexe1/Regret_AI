import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { decisionPath } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { formatRelative } from '@/lib/format';
import { domainLabel } from '@/lib/labels';
import { riskLabel, riskTone } from '@/lib/tone';
import type { DecisionSummary } from '@/lib/decisionSummary';

/**
 * Shared grid so the header labels and every row line up as real columns.
 *
 * Table layout starts at `xl`, not `lg`: the fixed columns total roughly 35rem
 * and at 1024px the content area is only ~46rem once the sidebar and gutters
 * are removed, which squeezed the title column to almost nothing.
 */
export const DECISION_GRID =
  'grid gap-x-6 gap-y-3 xl:grid-cols-[minmax(0,1fr)_6rem_11rem_9.5rem_7rem_1rem] xl:items-center';

function countLabel(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

export interface DecisionRowProps {
  summary: DecisionSummary;
}

export function DecisionRow({ summary }: DecisionRowProps) {
  const { decision, risk, statusLabel, statusTone, uncertaintyCount, experimentCount } = summary;

  const signals = [
    uncertaintyCount > 0
      ? countLabel(uncertaintyCount, 'uncertainty', 'uncertainties')
      : null,
    experimentCount > 0 ? countLabel(experimentCount, 'experiment', 'experiments') : null,
  ].filter((signal): signal is string => signal !== null);

  return (
    <Link
      to={decisionPath(decision.id)}
      className={cn(
        'group px-5 py-4 transition-colors duration-150 hover:bg-surface-raised',
        DECISION_GRID,
      )}
    >
      <div className="min-w-0">
        <p className="truncate text-card-title text-ink">{decision.title}</p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-micro text-ink-muted">
          <span>{domainLabel[decision.domain]}</span>
          <span aria-hidden>·</span>
          <span className="numeric">{decision.id}</span>
        </p>
      </div>

      <Badge tone={riskTone[risk]} size="sm" dot className="justify-self-start">
        {riskLabel[risk]}
      </Badge>

      <Badge tone={statusTone} size="sm" variant="outline" className="justify-self-start">
        {statusLabel}
      </Badge>

      {/* Counts stay on one line per signal so the column reads vertically. */}
      <div className="text-small text-ink-secondary">
        {signals.length > 0 ? (
          signals.map((signal) => (
            <p key={signal} className="numeric truncate">
              {signal}
            </p>
          ))
        ) : (
          <p className="text-ink-muted">No signals yet</p>
        )}
      </div>

      <p className="text-small text-ink-muted xl:text-right">
        Updated {formatRelative(decision.updatedAt)}
      </p>

      <ChevronRight
        className="hidden size-4 shrink-0 text-ink-muted transition-colors group-hover:text-ink-secondary xl:block"
        aria-hidden
      />
    </Link>
  );
}
