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
import { Button, buttonClasses } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonText } from '@/components/ui/Skeleton';
import { ROUTES } from '@/data/navigation';
import { useDecisionHistory, type DecisionFilterId } from '@/hooks/useDecisionHistory';

export function DecisionHistoryPage() {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<DecisionFilterId>('all');

  const { rows, loadedCount, isWorkspaceEmpty, isLoading, error, hasMore, isLoadingMore, loadMore, retry } =
    useDecisionHistory({ query, filter });

  const clearFilters = () => {
    setQuery('');
    setFilter('all');
  };

  return (
    <PageContainer
      eyebrow="Archive"
      title="Decision history"
      description="Every decision you've stress-tested."
      actions={
        <Link to={ROUTES.newDecision} className={buttonClasses({ variant: 'primary', size: 'md' })}>
          <Plus className="size-4" aria-hidden />
          New Decision
        </Link>
      }
    >
      {error ? (
        <ErrorState
          title="Unable to load your decisions"
          description={error.message}
          detail={error.requestId ? `Request ID: ${error.requestId}` : undefined}
          action={
            <button
              type="button"
              onClick={retry}
              className="text-small font-medium text-accent-ink underline-offset-4 hover:underline"
            >
              Retry
            </button>
          }
        />
      ) : isLoading ? (
        <SkeletonText lines={8} />
      ) : isWorkspaceEmpty ? (
        <DecisionHistoryEmpty />
      ) : (
        <div className="space-y-6">
          <DecisionFilterBar
            query={query}
            onQueryChange={setQuery}
            filter={filter}
            onFilterChange={setFilter}
            resultCount={rows.length}
            loadedCount={loadedCount}
          />

          {rows.length > 0 ? (
            <>
              <DecisionList rows={rows} />
              {hasMore ? (
                <div className="flex justify-center">
                  <Button variant="secondary" size="md" loading={isLoadingMore} onClick={loadMore}>
                    Load more
                  </Button>
                </div>
              ) : null}
            </>
          ) : (
            <DecisionHistoryNoMatches onClear={clearFilters} />
          )}
        </div>
      )}
    </PageContainer>
  );
}
