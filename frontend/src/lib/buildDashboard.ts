import { FileText, FlaskConical, ScanSearch, ShieldQuestion, SquarePen, TriangleAlert } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ApiDecision } from '@/api/types';
import { learningTypeTone } from '@/lib/buildDecisionMemory';
import { formatRelative } from '@/lib/format';
import { statusLabel } from '@/lib/labels';
import type { Tone } from '@/types';
import type { DashboardData } from '@/hooks/useDashboard';

export interface DashboardMetric {
  label: string;
  value: number;
  icon: LucideIcon;
  tone: Tone;
  help: string;
}

export interface DashboardSignal {
  label: string;
  tone: Tone;
}

export interface RecentDecisionRow {
  id: string;
  title: string;
  statusLabel: string;
  statusTone: Tone;
  experimentCount: number;
  updatedLabel: string;
}

export interface PortfolioBand {
  label: string;
  tone: Tone;
  count: number;
}

export interface OpenExperimentRow {
  id: string;
  decisionId: string;
  title: string;
  statusLabel: string;
  statusTone: Tone;
  durationDays: number | null;
}

export interface ActivityEvent {
  id: string;
  icon: LucideIcon;
  label: string;
  detail: string;
  timestamp: string;
  tone: Tone;
}

/** One recent Decision Memory learning, for the dashboard's "Recent
 * Decision Learnings" card - REGRET ENGINE 2.0. */
export interface RecentLearningRow {
  id: string;
  decisionId: string;
  decisionTitle: string;
  statement: string;
  tone: Tone;
  timestamp: string;
}

const STATUS_TONE: Record<ApiDecision['status'], Tone> = {
  draft: 'neutral',
  queued: 'neutral',
  analyzing: 'info',
  completed: 'success',
  needs_validation: 'warning',
  archived: 'neutral',
};

/**
 * Derives every dashboard figure from real decisions + experiments -
 * nothing here is a placeholder count. `regretIndex`/`fragility`-style
 * fabricated metrics from the old mock data are gone entirely; a
 * "riskLevel" band is approximated only from decision status
 * (`needs_validation` -> medium, everything else -> low) since the
 * backend does not expose a numeric risk score on the decision itself.
 */
export function buildDashboardMetrics(data: DashboardData): DashboardMetric[] {
  const { decisions, experimentsByDecisionId } = data;
  const needsValidation = decisions.filter((d) => d.status === 'needs_validation').length;
  const openExperiments = [...experimentsByDecisionId.values()]
    .flat()
    .filter((e) => e.status === 'recommended' || e.status === 'active' || e.status === 'planned').length;
  const completed = decisions.filter((d) => d.status === 'completed').length;

  return [
    {
      label: 'Decisions in workspace',
      value: decisions.length,
      icon: ScanSearch,
      tone: 'neutral',
      help: 'Decisions created in this workspace, most recent first.',
    },
    {
      label: 'Needs validation',
      value: needsValidation,
      icon: TriangleAlert,
      tone: 'warning',
      help: 'Decisions with a recommended experiment that has not been run yet.',
    },
    {
      label: 'Open experiments',
      value: openExperiments,
      icon: FlaskConical,
      tone: 'info',
      help: 'Experiments recommended, planned, or currently active.',
    },
    {
      label: 'Analysis complete',
      value: completed,
      icon: ShieldQuestion,
      tone: 'success',
      help: 'Decisions whose full analysis pipeline has completed.',
    },
  ];
}

export function buildRecentDecisionRows(data: DashboardData, limit = 5): RecentDecisionRow[] {
  return [...data.decisions]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, limit)
    .map((decision) => ({
      id: decision.id,
      title: decision.title,
      statusLabel: statusLabel[decision.status],
      statusTone: STATUS_TONE[decision.status],
      experimentCount: data.experimentsByDecisionId.get(decision.id)?.length ?? 0,
      updatedLabel: formatRelative(decision.updated_at),
    }));
}

export function buildPortfolioBands(data: DashboardData): PortfolioBand[] {
  const counts = new Map<ApiDecision['status'], number>();
  for (const decision of data.decisions) {
    counts.set(decision.status, (counts.get(decision.status) ?? 0) + 1);
  }
  return [...counts.entries()]
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({ label: statusLabel[status], tone: STATUS_TONE[status], count }));
}

export function buildOpenExperimentRows(data: DashboardData, limit = 5): OpenExperimentRow[] {
  const rows: OpenExperimentRow[] = [];
  for (const [decisionId, experiments] of data.experimentsByDecisionId.entries()) {
    for (const experiment of experiments) {
      if (experiment.status === 'recommended' || experiment.status === 'active' || experiment.status === 'planned') {
        rows.push({
          id: experiment.id,
          decisionId,
          title: experiment.title,
          statusLabel: experiment.status,
          statusTone: experiment.status === 'active' ? 'info' : 'accent',
          durationDays: experiment.duration_days,
        });
      }
    }
  }
  return rows.sort((a) => (a.statusLabel === 'active' ? -1 : 1)).slice(0, limit);
}

export function buildActivityEvents(data: DashboardData, limit = 5): ActivityEvent[] {
  const events: (ActivityEvent & { at: string })[] = [];

  for (const decision of data.decisions) {
    events.push({
      id: `decision-created-${decision.id}`,
      icon: SquarePen,
      label: 'Decision created',
      detail: decision.title,
      timestamp: formatRelative(decision.created_at),
      tone: 'neutral',
      at: decision.created_at,
    });
    if (decision.updated_at !== decision.created_at) {
      events.push({
        id: `decision-updated-${decision.id}`,
        icon: FileText,
        label: 'Decision updated',
        detail: decision.title,
        timestamp: formatRelative(decision.updated_at),
        tone: 'accent',
        at: decision.updated_at,
      });
    }
  }

  for (const experiments of data.experimentsByDecisionId.values()) {
    for (const experiment of experiments) {
      events.push({
        id: `experiment-${experiment.id}`,
        icon: FlaskConical,
        label: `Experiment ${experiment.status}`,
        detail: experiment.title,
        timestamp: formatRelative(experiment.created_at),
        tone: experiment.status === 'completed' ? 'success' : 'info',
        at: experiment.created_at,
      });
    }
  }

  return events
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, limit)
    .map(({ at: _at, ...event }) => event);
}

/** Summary shown on the dashboard's "Historical Lessons" card - a single,
 * bounded count, never the full historical-context detail (that lives on
 * AnalysisPage/DecisionDetailPage). REGRET ENGINE 2.0. */
export interface HistoricalLessonsSummary {
  /** Count of VALIDATED learnings (assumption_validated/threshold_validated)
   * surfaced across the decisions checked - "could apply to your recent
   * decisions" language, never "will apply" or a probability claim. */
  validatedLearningCount: number;
  /** How many of the checked decisions actually had relevant history. */
  decisionsWithHistoryCount: number;
}

/**
 * Deterministic, bounded summary for the dashboard's "Historical Lessons"
 * card - counts real `HistoricalInsight`s already fetched by
 * `useDashboard` (bounded to a handful of decisions, see
 * `HISTORICAL_CONTEXT_DECISIONS_LIMIT`), never a separate computation.
 */
export function buildHistoricalLessonsSummary(data: DashboardData): HistoricalLessonsSummary {
  let validatedLearningCount = 0;
  let decisionsWithHistoryCount = 0;

  for (const context of data.historicalContextByDecisionId.values()) {
    if (context.found) decisionsWithHistoryCount += 1;
    for (const insight of context.relevant_learnings) {
      if (insight.learning_type === 'assumption_validated' || insight.learning_type === 'threshold_validated') {
        validatedLearningCount += 1;
      }
    }
  }

  return { validatedLearningCount, decisionsWithHistoryCount };
}

/**
 * Recent, real Decision Memory learnings across the workspace's decisions
 * - REGRET ENGINE 2.0. Every row is a real, persisted `MemoryLearning`;
 * nothing here is a placeholder or a re-scored summary.
 */
export function buildRecentLearnings(data: DashboardData, limit = 5): RecentLearningRow[] {
  const decisionTitleById = new Map(data.decisions.map((d) => [d.id, d.title]));
  const rows: (RecentLearningRow & { at: string })[] = [];

  for (const [decisionId, learnings] of data.learningsByDecisionId.entries()) {
    for (const learning of learnings) {
      rows.push({
        id: learning.learning_id,
        decisionId,
        decisionTitle: decisionTitleById.get(decisionId) ?? 'Untitled decision',
        statement: learning.statement,
        tone: learningTypeTone(learning.learning_type),
        timestamp: formatRelative(learning.created_at),
        at: learning.created_at,
      });
    }
  }

  return rows
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, limit)
    .map(({ at: _at, ...row }) => row);
}


