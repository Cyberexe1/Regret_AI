import { FilterX, SquarePen } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ROUTES } from '@/data/navigation';

/** Nothing in the workspace yet. */
export function DecisionHistoryEmpty() {
  return (
    <EmptyState
      icon={SquarePen}
      title="Your first important decision starts here."
      description="Describe a decision you are about to commit to, and the engine will find the assumptions it rests on and what would make it fail."
      action={
        <Link to={ROUTES.newDecision} className={buttonClasses({ variant: 'primary', size: 'md' })}>
          Stress-test a decision
        </Link>
      }
    />
  );
}

export interface DecisionHistoryNoMatchesProps {
  onClear: () => void;
}

/** The workspace has decisions, but the current search or filter excludes them. */
export function DecisionHistoryNoMatches({ onClear }: DecisionHistoryNoMatchesProps) {
  return (
    <EmptyState
      icon={FilterX}
      title="No decisions match this view"
      description="Try a different risk band, or clear the search to see everything again."
      action={
        <Button variant="secondary" size="sm" onClick={onClear}>
          Clear filters
        </Button>
      }
    />
  );
}
