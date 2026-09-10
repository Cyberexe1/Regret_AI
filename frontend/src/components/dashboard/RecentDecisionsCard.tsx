import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { FileText } from 'lucide-react';
import { decisionPath, ROUTES } from '@/data/navigation';
import type { RecentDecisionRow } from '@/lib/buildDashboard';

export interface RecentDecisionsCardProps {
  rows: RecentDecisionRow[];
}

function DecisionRow({ row }: { row: RecentDecisionRow }) {
  return (
    <Link
      to={decisionPath(row.id)}
      className="group flex flex-col gap-3 px-5 py-4 transition-colors duration-150 hover:bg-surface-raised sm:flex-row sm:items-center sm:gap-4"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-card-title text-ink">{row.title}</p>
        <p className="numeric mt-0.5 text-micro text-ink-muted">{row.id}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={row.statusTone} size="sm" dot>
          {row.statusLabel}
        </Badge>
        {row.experimentCount > 0 ? (
          <Badge tone="neutral" size="sm" variant="outline">
            {row.experimentCount} experiment{row.experimentCount === 1 ? '' : 's'}
          </Badge>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-2 sm:w-28 sm:justify-end">
        <span className="text-small text-ink-muted">{row.updatedLabel}</span>
        <ChevronRight
          className="size-4 shrink-0 text-ink-muted transition-colors group-hover:text-ink-secondary"
          aria-hidden
        />
      </div>
    </Link>
  );
}

export function RecentDecisionsCard({ rows }: RecentDecisionsCardProps) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-hairline px-5 py-4 md:px-6">
        <div>
          <CardTitle>Recent decisions</CardTitle>
          <p className="mt-0.5 text-small text-ink-muted">Sorted by most recently updated</p>
        </div>
        <Link
          to={ROUTES.decisions}
          className="shrink-0 text-small text-accent-ink transition-colors hover:text-ink"
        >
          View all
        </Link>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          size="inline"
          icon={FileText}
          title="No decisions yet"
          description="Start by testing a decision."
        />
      ) : (
        <div className="divide-y divide-hairline">
          {rows.map((row) => (
            <DecisionRow key={row.id} row={row} />
          ))}
        </div>
      )}
    </Card>
  );
}
