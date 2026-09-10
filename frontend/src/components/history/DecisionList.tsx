import type { ApiDecision } from '@/api/types';
import { cn } from '@/lib/cn';
import { DECISION_GRID, DecisionRow } from './DecisionRow';

export interface DecisionListProps {
  rows: ApiDecision[];
}

export function DecisionList({ rows }: DecisionListProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-surface">
      {/* Column labels, shown once the grid actually has columns. */}
      <div
        aria-hidden
        className={cn('hidden border-b border-hairline bg-header-bar px-5 py-2.5 xl:grid', DECISION_GRID)}
      >
        <span className="eyebrow">Decision</span>
        <span className="eyebrow">Status</span>
        <span className="eyebrow">Created</span>
        <span className="eyebrow xl:text-right">Updated</span>
        <span />
      </div>

      <ul className="divide-y divide-hairline">
        {rows.map((decision) => (
          <li key={decision.id}>
            <DecisionRow decision={decision} />
          </li>
        ))}
      </ul>
    </div>
  );
}
