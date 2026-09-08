import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import {
  openExperiments,
  openExperimentTotal,
  type ExperimentProgressRow,
} from '@/data/dashboard';
import { ROUTES } from '@/data/navigation';
import { formatDays } from '@/lib/format';

function ExperimentRow({ row }: { row: ExperimentProgressRow }) {
  return (
    <div className="px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <p className="min-w-0 text-card-title text-ink">{row.title}</p>
        <Badge tone={row.signal.tone} size="sm" dot>
          {row.signal.label}
        </Badge>
      </div>

      <Progress
        className="mt-4"
        value={row.progress}
        tone="accent"
        size="sm"
        label="Progress"
        showValue
        valueSuffix="%"
      />

      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <p className="text-small text-ink-muted">
          Expected completion in {formatDays(row.daysRemaining)}
        </p>
        <Link
          to={ROUTES.experiments}
          className="inline-flex items-center gap-1.5 text-small text-accent-ink transition-colors hover:text-ink"
        >
          View experiment
          <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      </div>
    </div>
  );
}

export function OpenExperimentsCard() {
  return (
    <Card padding="none" className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-hairline px-5 py-4 md:px-6">
        <div>
          <CardTitle>Open experiments</CardTitle>
          <p className="mt-0.5 text-small text-ink-muted">
            Showing {openExperiments.length} of {openExperimentTotal} running
          </p>
        </div>
        <Link
          to={ROUTES.experiments}
          className="shrink-0 text-small text-accent-ink transition-colors hover:text-ink"
        >
          View all
        </Link>
      </div>

      <div className="divide-y divide-hairline">
        {openExperiments.map((row) => (
          <ExperimentRow key={row.id} row={row} />
        ))}
      </div>
    </Card>
  );
}
