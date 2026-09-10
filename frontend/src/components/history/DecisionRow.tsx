import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ApiDecision } from '@/api/types';
import { Badge } from '@/components/ui/Badge';
import { decisionPath } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { formatRelative } from '@/lib/format';
import { statusLabel } from '@/lib/labels';
import type { Tone } from '@/types';

/**
 * Shared grid so the header labels and every row line up as real columns.
 *
 * Table layout starts at `xl`, not `lg`: the fixed columns total roughly 35rem
 * and at 1024px the content area is only ~46rem once the sidebar and gutters
 * are removed, which squeezed the title column to almost nothing.
 */
export const DECISION_GRID =
  'grid gap-x-6 gap-y-3 xl:grid-cols-[minmax(0,1fr)_11rem_9.5rem_7rem_1rem] xl:items-center';

const STATUS_TONE: Record<ApiDecision['status'], Tone> = {
  draft: 'neutral',
  queued: 'neutral',
  analyzing: 'info',
  completed: 'success',
  needs_validation: 'warning',
  archived: 'neutral',
};

export interface DecisionRowProps {
  decision: ApiDecision;
}

export function DecisionRow({ decision }: DecisionRowProps) {
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
          <span className="numeric truncate">{decision.id}</span>
        </p>
      </div>

      <Badge tone={STATUS_TONE[decision.status]} size="sm" dot className="justify-self-start">
        {statusLabel[decision.status]}
      </Badge>

      <p className="text-small text-ink-secondary">Created {formatRelative(decision.created_at)}</p>

      <p className="text-small text-ink-muted xl:text-right">Updated {formatRelative(decision.updated_at)}</p>

      <ChevronRight
        className="hidden size-4 shrink-0 text-ink-muted transition-colors group-hover:text-ink-secondary xl:block"
        aria-hidden
      />
    </Link>
  );
}
