import { Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { CrossDecisionPatternRow } from '@/types/report';

export interface CrossDecisionPatternsPanelProps {
  rows: CrossDecisionPatternRow[];
  isLoading?: boolean;
}

/**
 * REGRET ENGINE 2.0's "WHAT YOUR PAST DECISIONS TEACH" section (Step
 * 23): every real Cross-Decision Pattern relevant to THIS decision -
 * i.e. one that names this decision as supporting or contradicting
 * evidence (`GET /decisions/{id}/patterns`).
 *
 * Deliberately never phrased as a prediction about this decision -
 * every `statement` is the backend's own already-hedged wording ("in
 * your past decisions...", never "this decision will..."). Current
 * evidence for THIS decision is presented elsewhere on the page and
 * stays visually more prominent - this panel is explicitly historical
 * context, not authority (spec sections 7/13).
 */
export function CrossDecisionPatternsPanel({ rows, isLoading = false }: CrossDecisionPatternsPanelProps) {
  if (isLoading) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Checking your decision history…"
        description="Looking for recurring patterns from your own past decisions."
      />
    );
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Nothing recurring yet"
        description="No cross-decision pattern currently names this decision as supporting or contradicting evidence."
      />
    );
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <Card key={row.patternId} variant="inset">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <p className="text-card-title text-ink">{row.title}</p>
            <Badge tone={row.statusTone} size="sm" dot>
              {row.statusLabel}
            </Badge>
          </div>

          <p className="mt-2 text-small text-ink-secondary">{row.statement}</p>

          <dl className="mt-3 grid grid-cols-2 gap-3 border-t border-hairline pt-3 sm:grid-cols-4">
            <div>
              <dt className="text-micro text-ink-muted">Evidence count</dt>
              <dd className="numeric mt-0.5 text-small text-ink">{row.occurrenceCount}</dd>
            </div>
            <div>
              <dt className="text-micro text-ink-muted">Supporting decisions</dt>
              <dd className="numeric mt-0.5 text-small text-ink">{row.supportingDecisionCount}</dd>
            </div>
            {row.contradictingDecisionCount > 0 ? (
              <div>
                <dt className="text-micro text-ink-muted">Contradicting</dt>
                <dd className="numeric mt-0.5 text-small text-ink">{row.contradictingDecisionCount}</dd>
              </div>
            ) : null}
            <div>
              <dt className="text-micro text-ink-muted">Confidence</dt>
              <dd className="mt-0.5">
                <Badge tone={row.confidenceTone} size="sm">
                  {row.confidenceLabel}
                </Badge>
              </dd>
            </div>
          </dl>

          <p className="mt-3 border-t border-hairline pt-3 text-micro text-ink-muted">
            {row.confidenceBasis}
          </p>
        </Card>
      ))}
    </div>
  );
}
