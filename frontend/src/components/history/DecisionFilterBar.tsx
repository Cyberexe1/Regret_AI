import { Search } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import {
  DECISION_FILTERS,
  DECISION_SORTS,
  type DecisionFilterId,
  type DecisionSortId,
} from '@/hooks/useDecisionHistory';
import { cn } from '@/lib/cn';

export interface DecisionFilterBarProps {
  query: string;
  onQueryChange: (value: string) => void;
  filter: DecisionFilterId;
  onFilterChange: (value: DecisionFilterId) => void;
  sort: DecisionSortId;
  onSortChange: (value: DecisionSortId) => void;
  /** Shown beside the filters so the current view is always accounted for. */
  resultCount: number;
  totalCount: number;
}

export function DecisionFilterBar({
  query,
  onQueryChange,
  filter,
  onFilterChange,
  sort,
  onSortChange,
  resultCount,
  totalCount,
}: DecisionFilterBarProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          type="search"
          icon={Search}
          placeholder="Search decisions"
          aria-label="Search decisions"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          fieldClassName="flex-1"
        />
        <Select
          aria-label="Sort decisions"
          options={DECISION_SORTS.map((option) => ({ ...option }))}
          value={sort}
          onChange={(event) => onSortChange(event.target.value as DecisionSortId)}
          fieldClassName="sm:w-52"
        />
      </div>

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
          {resultCount === totalCount
            ? `${totalCount} decisions`
            : `${resultCount} of ${totalCount} decisions`}
        </p>
      </div>
    </div>
  );
}
