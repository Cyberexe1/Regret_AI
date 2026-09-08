import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  DecisionFilterBar,
  DecisionHistoryEmpty,
  DecisionHistoryNoMatches,
  DecisionList,
} from '@/components/history';
import { buttonClasses } from '@/components/ui/Button';
import { ROUTES } from '@/data/navigation';
import {
  useDecisionHistory,
  type DecisionFilterId,
  type DecisionSortId,
} from '@/hooks/useDecisionHistory';

export function DecisionHistoryPage() {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<DecisionFilterId>('all');
  const [sort, setSort] = useState<DecisionSortId>('updated');

  const { rows, totalCount, isWorkspaceEmpty } = useDecisionHistory({ query, filter, sort });

  const clearFilters = () => {
    setQuery('');
    setFilter('all');
  };

  return (
    <PageContainer
      eyebrow="Archive"
      title="Decision history"
      description="Every important decision you've stress-tested."
      actions={
        <Link
          to={ROUTES.newDecision}
          className={buttonClasses({ variant: 'primary', size: 'md' })}
        >
          <Plus className="size-4" aria-hidden />
          New Decision
        </Link>
      }
    >
      {isWorkspaceEmpty ? (
        <DecisionHistoryEmpty />
      ) : (
        <div className="space-y-6">
          <DecisionFilterBar
            query={query}
            onQueryChange={setQuery}
            filter={filter}
            onFilterChange={setFilter}
            sort={sort}
            onSortChange={setSort}
            resultCount={rows.length}
            totalCount={totalCount}
          />

          {rows.length > 0 ? (
            <DecisionList rows={rows} />
          ) : (
            <DecisionHistoryNoMatches onClear={clearFilters} />
          )}
        </div>
      )}
    </PageContainer>
  );
}
