import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { Layers } from 'lucide-react';
import { cn } from '@/lib/cn';
import { toneText } from '@/lib/tone';
import type { ReportAssumptionRow } from '@/types/report';

export interface AssumptionsSectionProps {
  assumptions: ReportAssumptionRow[];
}

export function AssumptionsSection({ assumptions }: AssumptionsSectionProps) {
  const tally = {
    total: assumptions.length,
    supported: assumptions.filter((a) => a.evidenceStatusLabel === 'Supported').length,
    contradicted: assumptions.filter((a) => a.evidenceStatusLabel === 'Contradicted').length,
    notAddressed: assumptions.filter((a) => a.evidenceStatusLabel === 'Not addressed').length,
  };

  if (assumptions.length === 0) {
    return (
      <EmptyState
        icon={Layers}
        title="No assumptions identified"
        description="The Assumption Hunter did not identify any assumptions for this decision, or the analysis has not reached this stage yet."
      />
    );
  }

  const summary = [
    { label: 'identified', value: tally.total, tone: 'neutral' as const },
    { label: 'supported', value: tally.supported, tone: 'success' as const },
    { label: 'contradicted', value: tally.contradicted, tone: 'danger' as const },
    { label: 'not addressed', value: tally.notAddressed, tone: 'warning' as const },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {summary.map((item) => (
          <div key={item.label} className="rounded-xl border border-hairline bg-surface px-5 py-4">
            <div className="flex items-baseline gap-2">
              <span className={cn('numeric text-metric', toneText[item.tone])}>{item.value}</span>
              <span className="text-small text-ink-secondary">{item.label}</span>
            </div>
          </div>
        ))}
      </div>

      <ul className="divide-y divide-hairline overflow-hidden rounded-xl border border-hairline bg-surface">
        {assumptions.map((assumption) => (
          <li key={assumption.id} className="flex gap-4 px-5 py-4 md:px-6">
            <div className="min-w-0 flex-1">
              <p className="text-small text-ink">{assumption.statement}</p>
              {assumption.note ? (
                <p className="mt-1 text-small text-ink-muted">{assumption.note}</p>
              ) : null}
            </div>
            <Badge
              tone={assumption.evidenceStatusTone}
              size="sm"
              variant="outline"
              className="mt-0.5 shrink-0 self-start"
            >
              {assumption.evidenceStatusLabel}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}
