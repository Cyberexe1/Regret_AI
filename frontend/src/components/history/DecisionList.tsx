import { cn } from '@/lib/cn';
import type { DecisionSummary } from '@/lib/decisionSummary';
import { DECISION_GRID, DecisionRow } from './DecisionRow';

export interface DecisionListProps {
  rows: DecisionSummary[];
}

export function DecisionList({ rows }: DecisionListProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-surface">
      {/* Column labels, shown once the grid actually has columns. */}
      <div
        aria-hidden
        className={cn(
          'hidden border-b border-hairline bg-surface-raised/60 px-5 py-2.5 lg:grid',
          DECISION_GRID,
        )}
      >
        <span className="eyebrow">Decision</span>
        <span className="eyebrow">Risk</span>
        <span className="eyebrow">Status</span>
        <span className="eyebrow">Signals</span>
        <span className="eyebrow lg:text-right">Updated</span>
        <span />
      </div>

      <ul className="divide-y divide-hairline">
        {rows.map((summary) => (
          <li key={summary.decision.id}>
            <DecisionRow summary={summary} />
          </li>
        ))}
      </ul>
    </div>
  );
}
