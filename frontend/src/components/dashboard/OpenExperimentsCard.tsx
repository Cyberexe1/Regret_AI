import { ArrowRight, FlaskConical } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { decisionPath, ROUTES } from '@/data/navigation';
import type { OpenExperimentRow } from '@/lib/buildDashboard';

export interface OpenExperimentsCardProps {
  rows: OpenExperimentRow[];
  totalCount: number;
}

function ExperimentRow({ row }: { row: OpenExperimentRow }) {
  return (
    <div className="min-w-0 px-4 py-4 sm:px-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <p className="min-w-0 flex-1 break-words text-card-title text-ink">{row.title}</p>
        <Badge tone={row.statusTone} size="sm" dot>
          {row.statusLabel}
        </Badge>
      </div>

      <div className="mt-3 flex min-w-0 flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <p className="min-w-0 break-words text-small text-ink-muted">
          {row.durationDays !== null ? `${row.durationDays}-day experiment` : 'Duration not set'}
        </p>
        <Link
          to={decisionPath(row.decisionId)}
          className="inline-flex max-w-full items-center gap-1.5 text-small text-accent-ink transition-colors hover:text-ink"
        >
          <span className="break-words">View experiment</span>
          <ArrowRight className="size-3.5 shrink-0" aria-hidden />
        </Link>
      </div>
    </div>
  );
}

export function OpenExperimentsCard({ rows, totalCount }: OpenExperimentsCardProps) {
  return (
    <Card padding="none" className="flex h-full min-w-0 flex-col overflow-hidden">
      <div className="flex min-w-0 items-start justify-between gap-3 border-b border-hairline px-4 py-4 sm:items-center sm:gap-4 sm:px-5 md:px-6">
        <div className="min-w-0">
          <CardTitle>Open experiments</CardTitle>
          <p className="numeric mt-0.5 break-words text-small text-ink-muted">
            Showing {rows.length} of {totalCount}
          </p>
        </div>
        <Link
          to={ROUTES.experiments}
          className="shrink-0 whitespace-nowrap text-small text-accent-ink transition-colors hover:text-ink"
        >
          View all
        </Link>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          size="inline"
          icon={FlaskConical}
          title="No open experiments"
          description="Recommended experiments will appear here once analysis completes."
        />
      ) : (
        <div className="min-w-0 divide-y divide-hairline">
          {rows.map((row) => (
            <ExperimentRow key={row.id} row={row} />
          ))}
        </div>
      )}
    </Card>
  );
}
