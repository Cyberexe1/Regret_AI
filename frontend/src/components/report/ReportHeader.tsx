import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { ApiDecision } from '@/api/types';
import { Badge } from '@/components/ui/Badge';
import { ROUTES } from '@/data/navigation';
import { statusLabel } from '@/lib/labels';

export interface ReportHeaderProps {
  decision: ApiDecision;
}

export function ReportHeader({ decision }: ReportHeaderProps) {
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
            <span className="numeric text-micro text-ink-muted">{decision.id}</span>
          </div>

          <h2 className="mt-3 text-page-title text-ink">{decision.title}</h2>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Badge tone={decision.status === 'needs_validation' ? 'warning' : 'neutral'} dot>
              {statusLabel[decision.status]}
            </Badge>
          </div>

          <p className="mt-5 max-w-2xl text-body text-ink-secondary">{decision.description}</p>
        </div>
      </div>
    </header>
  );
}
