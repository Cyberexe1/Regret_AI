import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { riskLabel, riskTone, toneText } from '@/lib/tone';
import type { DecisionReport } from '@/types';

export interface ReportHeaderProps {
  report: DecisionReport;
}

export function ReportHeader({ report }: ReportHeaderProps) {
  return (
    <header>
      <Link
        to={ROUTES.decisions}
        className="inline-flex items-center gap-1.5 text-small text-ink-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="size-3.5" aria-hidden />
        Decision history
      </Link>

      <div className="mt-5 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="eyebrow">Decision report</p>
            <span className="numeric text-micro text-ink-muted">{report.decisionId}</span>
          </div>

          <h2 className="mt-3 text-page-title text-ink">{report.title}</h2>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Badge tone="warning" dot>
              {report.statusLabel}
            </Badge>
            <Badge tone="neutral" variant="outline">
              Stress test complete
            </Badge>
          </div>

          <p className="mt-5 max-w-2xl text-body text-ink-secondary">{report.summary}</p>
        </div>

        {/* Risk level, given its own block so it reads at a glance */}
        <div className="shrink-0 rounded-xl border border-hairline bg-surface-inset px-6 py-5 lg:w-52">
          <p className="eyebrow">Main risk level</p>
          <p
            className={cn(
              'mt-2 text-headline uppercase',
              toneText[riskTone[report.riskLevel]],
            )}
          >
            {riskLabel[report.riskLevel]}
          </p>
          <p className="mt-3 text-small text-ink-muted">
            Driven by unresolved uncertainties, not by the size of the commitment.
          </p>
        </div>
      </div>
    </header>
  );
}
