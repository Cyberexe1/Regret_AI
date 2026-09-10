import { Search } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { DECISION_FILTERS, type DecisionFilterId } from '@/hooks/useDecisionHistory';
import { cn } from '@/lib/cn';

export interface DecisionFilterBarProps {
  query: string;
  onQueryChange: (value: string) => void;
  filter: DecisionFilterId;
  onFilterChange: (value: DecisionFilterId) => void;
  /** Shown beside the filters so the current view is always accounted for. */
  resultCount: number;
  loadedCount: number;
}

export function DecisionFilterBar({
  query,
  onQueryChange,
  filter,
  onFilterChange,
  resultCount,
  loadedCount,
}: DecisionFilterBarProps) {
  return (
    <div className="space-y-4">
      <Input
        type="search"
        icon={Search}
        placeholder="Search decisions"
        aria-label="Search decisions"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div role="group" aria-label="Filter decisions" className="flex flex-wrap gap-2">
          {DECISION_FILTERS.map((option) => {
            const active = option.id === filter;

            return (
              <button
                key={option.id}
                type="button"
                aria-pressed={active}
                onClick={() => onFilterChange(option.id)}
                className={cn(
                  'rounded-md border px-3 py-1.5 text-small font-medium transition-colors duration-150',
                  active
                    ? 'border-accent-line bg-accent-soft text-ink'
                    : 'border-hairline bg-surface text-ink-secondary hover:border-hairline-strong hover:text-ink',
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>

        <p className="numeric ml-auto text-small text-ink-muted">
          {resultCount === loadedCount ? `${loadedCount} decisions` : `${resultCount} of ${loadedCount} loaded`}
        </p>
      </div>
    </div>
  );
}
