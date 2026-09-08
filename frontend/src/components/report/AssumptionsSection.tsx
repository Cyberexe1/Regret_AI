import { Badge } from '@/components/ui/Badge';
import { summariseAssumptions } from '@/data/decisionReport';
import { cn } from '@/lib/cn';
import { assumptionSupportLabel, assumptionSupportTone, toneFill, toneText } from '@/lib/tone';
import type { DecisionReport } from '@/types';

export interface AssumptionsSectionProps {
  report: DecisionReport;
}

export function AssumptionsSection({ report }: AssumptionsSectionProps) {
  const tally = summariseAssumptions(report);

  const summary = [
    { label: 'identified', value: tally.total, tone: 'neutral' as const },
    { label: 'supported', value: tally.supported, tone: 'success' as const },
    { label: 'uncertain', value: tally.uncertain, tone: 'warning' as const },
    { label: 'unsupported', value: tally.unsupported, tone: 'danger' as const },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {summary.map((item) => (
          <div
            key={item.label}
            className="rounded-xl border border-hairline bg-surface px-5 py-4"
          >
            <div className="flex items-baseline gap-2">
              <span className={cn('numeric text-metric', toneText[item.tone])}>
                {item.value}
              </span>
              <span className="text-small text-ink-secondary">{item.label}</span>
            </div>
          </div>
        ))}
      </div>

      <ul className="divide-y divide-hairline overflow-hidden rounded-xl border border-hairline bg-surface">
        {report.assumptions.map((assumption) => (
          <li key={assumption.id} className="flex gap-4 px-5 py-4 md:px-6">
            <span
              className={cn(
                'mt-2 size-2 shrink-0 rounded-full',
                toneFill[assumptionSupportTone[assumption.support]],
              )}
              aria-hidden
            />
            <div className="min-w-0 flex-1">
              <p className="text-small text-ink">{assumption.statement}</p>
              <p className="mt-1 text-small text-ink-muted">{assumption.note}</p>
            </div>
            <Badge
              tone={assumptionSupportTone[assumption.support]}
              size="sm"
              variant="outline"
              className="mt-0.5 shrink-0 self-start"
            >
              {assumptionSupportLabel[assumption.support]}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}
