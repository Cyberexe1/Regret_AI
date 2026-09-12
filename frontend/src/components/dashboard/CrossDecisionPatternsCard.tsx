import { Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import type { CrossDecisionPatternRow } from '@/types/report';

export interface CrossDecisionPatternsCardProps {
  rows: CrossDecisionPatternRow[];
  isLoading?: boolean;
}

/**
 * REGRET ENGINE 2.0's Cross-Decision Learning Engine (Step 23):
 * "PATTERNS ACROSS YOUR DECISIONS" - a lightweight dashboard signal for
 * what keeps recurring across the user's OWN past decisions. Deliberately
 * bounded to the top few patterns by occurrence count (see
 * `buildCrossDecisionPatternRows`'s sort) - the full "show me why" detail
 * lives on the decision page, not here.
 *
 * Language mirrors `HistoricalLessonsCard`'s own careful framing: a
 * pattern is described as something that has recurred, never a
 * prediction about any specific future decision.
 */
export function CrossDecisionPatternsCard({ rows, isLoading = false }: CrossDecisionPatternsCardProps) {
  const topRows = rows.slice(0, 3);

  return (
    <Card padding="md" className="flex h-full min-w-0 flex-col overflow-hidden">
      <div className="flex min-w-0 items-center gap-2.5">
        <Sparkles className="size-4 shrink-0 text-ink-muted" aria-hidden />
        <CardTitle>Patterns across your decisions</CardTitle>
      </div>

      {isLoading ? (
        <div className="mt-3 space-y-3" role="status" aria-label="Checking for recurring patterns">
          {Array.from({ length: 3 }, (_, index) => (
            <div key={index} className="space-y-2 border-t border-hairline pt-3 first:border-t-0 first:pt-0">
              <Skeleton className="h-3.5 w-4/5" />
              <div className="flex min-w-0 items-center gap-2">
                <Skeleton className="h-5 w-20 shrink-0" />
                <Skeleton className="h-3 min-w-0 flex-1" />
              </div>
            </div>
          ))}
        </div>
      ) : topRows.length === 0 ? (
        <EmptyState
          size="inline"
          icon={Sparkles}
          title="No recurring patterns yet"
          description="Once you have a few completed decisions, REGRET ENGINE will surface what keeps recurring across them."
        />
      ) : (
        <ol className="mt-3 min-w-0 space-y-3">
          {topRows.map((row) => (
            <li key={row.patternId} className="min-w-0 border-t border-hairline pt-3 first:border-t-0 first:pt-0">
              <p className="break-words text-small text-ink">{row.title}</p>
              <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-2">
                <Badge tone={row.statusTone} size="sm" dot>
                  {row.statusLabel}
                </Badge>
                <span className="numeric break-words text-micro text-ink-muted">
                  {row.supportingDecisionCount} decision{row.supportingDecisionCount === 1 ? '' : 's'}
                </span>
                {row.contradictingDecisionCount > 0 ? (
                  <span className="numeric break-words text-micro text-ink-muted">
                    {row.contradictingDecisionCount} contradicting
                  </span>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
