import { History } from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { HistoricalLessonsSummary } from '@/lib/buildDashboard';

export interface HistoricalLessonsCardProps {
  summary: HistoricalLessonsSummary;
}

/**
 * REGRET ENGINE 2.0's small dashboard signal for Decision Similarity &
 * Historical Insight: a single, bounded count of validated learnings
 * from a handful of the workspace's most recent decisions - deliberately
 * NOT the full insight list (that lives on AnalysisPage/
 * DecisionDetailPage). Language is careful to say "could apply", never
 * "will apply" or a probability claim - historical insight is context,
 * not a verdict.
 */
export function HistoricalLessonsCard({ summary }: HistoricalLessonsCardProps) {
  return (
    <Card padding="md" className="flex h-full flex-col">
      <div className="flex items-center gap-2.5">
        <History className="size-4 shrink-0 text-ink-muted" aria-hidden />
        <CardTitle>Historical lessons</CardTitle>
      </div>

      {summary.validatedLearningCount > 0 ? (
        <p className="mt-3 text-small text-ink-secondary">
          {summary.validatedLearningCount} validated learning{summary.validatedLearningCount === 1 ? '' : 's'} from
          your past decisions could apply to your recent decisions.
        </p>
      ) : (
        <EmptyState
          size="inline"
          icon={History}
          title="No historical lessons yet"
          description="Once decisions share similar context, validated learnings will surface here."
        />
      )}
    </Card>
  );
}
