import { Gauge } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { CalibrationInsightRow } from '@/types/report';

export interface CalibrationInsightsCardProps {
  rows: CalibrationInsightRow[];
  isLoading?: boolean;
}

/**
 * REGRET ENGINE 2.0's Calibration Engine (Step 24): "WHAT YOUR PAST
 * DECISIONS REVEAL" - expected-vs-observed history for the user's OWN
 * completed experiments, grouped by variable. Deliberately bounded to
 * the top few variables by observation count (see
 * `buildCalibrationInsightRows`'s sort) - the full history lives on
 * `GET /learning/calibration`, not here.
 *
 * NO FALSE STATISTICS: every `explanation` shown is the backend's own
 * plain, count-based wording ("3 of 4 comparable experiments..."),
 * never a fabricated percentage or probability. This is historical
 * evidence about this user's own past predictions - never a prediction
 * about any specific future decision.
 */
export function CalibrationInsightsCard({ rows, isLoading = false }: CalibrationInsightsCardProps) {
  const topRows = rows.slice(0, 3);

  return (
    <Card padding="md" className="flex h-full flex-col">
      <div className="flex items-center gap-2.5">
        <Gauge className="size-4 shrink-0 text-ink-muted" aria-hidden />
        <CardTitle>What your past decisions reveal</CardTitle>
      </div>

      {isLoading ? (
        <p className="mt-3 text-small text-ink-secondary">Checking your calibration history…</p>
      ) : topRows.length === 0 ? (
        <EmptyState
          size="inline"
          icon={Gauge}
          title="Not enough history yet"
          description="Once you complete a few experiments, REGRET ENGINE will show how your expectations for a variable have compared to what actually happened."
        />
      ) : (
        <ol className="mt-3 space-y-3">
          {topRows.map((row) => (
            <li key={row.calibrationId} className="border-t border-hairline pt-3 first:border-t-0 first:pt-0">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-small text-ink">{row.variable}</p>
                <Badge tone={row.biasTone} size="sm" dot>
                  {row.biasLabel}
                </Badge>
              </div>
              <p className="mt-1.5 text-micro text-ink-muted">{row.explanation}</p>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
