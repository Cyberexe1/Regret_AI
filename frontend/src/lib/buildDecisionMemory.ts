/**
 * REGRET ENGINE 2.0: pure mapping from the real backend Decision Memory
 * response (`ApiDecisionMemoryResponse`) into presentational view models.
 *
 * Nothing here is fabricated - every field is either a real backend
 * `DecisionMemory`/`MemoryLearning` field or a deterministic
 * re-labelling of one, exactly like `buildDecisionReport.ts`. The
 * central "what we thought vs what we learned" distinction is preserved
 * explicitly via `DecisionMemorySummary.isValidated` /
 * `MemoryLearningRow.isValidated` - a preliminary memory (no experiment
 * result yet) never presents `outcomeSummary`/`finalAssessment` as
 * something that happened, because the backend itself leaves them
 * `null` until a real result exists.
 */
import type { ApiDecisionMemoryResponse, ApiMemoryLearning, LearningType } from '@/api/types';
import { formatRelative } from '@/lib/format';
import { confidencePercent } from '@/lib/reportModel';
import type { DecisionMemorySummary, MemoryLearningRow, MemoryTimelineEvent } from '@/types/report';
import type { Tone } from '@/types';

const LEARNING_TYPE_TONE: Record<LearningType, Tone> = {
  assumption_validated: 'success',
  assumption_weakened: 'warning',
  assumption_failed: 'danger',
  threshold_validated: 'success',
  threshold_failed: 'danger',
  threshold_inconclusive: 'warning',
  unexpected_result: 'warning',
  experiment_learning: 'neutral',
  decision_outcome: 'accent',
  unresolved_uncertainty: 'neutral',
};

const LEARNING_TYPE_LABEL: Record<LearningType, string> = {
  assumption_validated: 'Assumption validated',
  assumption_weakened: 'Assumption weakened',
  assumption_failed: 'Assumption failed',
  threshold_validated: 'Threshold validated',
  threshold_failed: 'Threshold failed',
  threshold_inconclusive: 'Threshold inconclusive',
  unexpected_result: 'Unexpected result',
  experiment_learning: 'Experiment learning',
  decision_outcome: 'Decision outcome',
  unresolved_uncertainty: 'Unresolved uncertainty',
};

const VALIDATED_LEARNING_TYPES = new Set<LearningType>([
  'assumption_validated',
  'assumption_weakened',
  'assumption_failed',
  'threshold_validated',
  'threshold_failed',
  'decision_outcome',
]);

export function learningTypeTone(type: LearningType): Tone {
  return LEARNING_TYPE_TONE[type];
}

export function learningTypeLabel(type: LearningType): string {
  return LEARNING_TYPE_LABEL[type];
}

function buildLearningRow(learning: ApiMemoryLearning): MemoryLearningRow {
  return {
    id: learning.learning_id,
    statement: learning.statement,
    typeLabel: learningTypeLabel(learning.learning_type),
    typeTone: learningTypeTone(learning.learning_type),
    isValidated: VALIDATED_LEARNING_TYPES.has(learning.learning_type),
    observedValue: learning.observed_value,
    expectedValue: learning.expected_value,
    varianceDescription: learning.variance_description,
    createdAtLabel: formatRelative(learning.created_at),
  };
}

/** Builds the "what we thought / what we learned" summary shown in the
 * Decision Memory panel. `hasMemory=false` means no memory has been
 * created yet at all (the decision hasn't even been analyzed) - distinct
 * from `isValidated=false`, which means a preliminary memory exists but
 * no experiment result has been observed yet. */
export function buildDecisionMemorySummary(
  response: ApiDecisionMemoryResponse,
): DecisionMemorySummary {
  const { memory, learnings } = response;

  if (memory === null) {
    return {
      hasMemory: false,
      isValidated: false,
      decisionSummary: '',
      originalAssessment: null,
      outcomeSummary: null,
      finalAssessment: null,
      confidencePercent: undefined,
      learnings: [],
      unresolvedUncertainties: [],
      experimentCount: 0,
      criticalAssumptionCount: 0,
      criticalThresholdCount: 0,
      criticalRegretScenarioCount: 0,
    };
  }

  return {
    hasMemory: true,
    isValidated: memory.stage === 'validated',
    decisionSummary: memory.decision_summary,
    originalAssessment: memory.original_assessment,
    outcomeSummary: memory.outcome_summary,
    finalAssessment: memory.final_assessment,
    confidencePercent: confidencePercent(memory.confidence),
    learnings: learnings.map(buildLearningRow),
    // While preliminary, unresolved_uncertainties on the memory itself
    // holds plain descriptive strings (nothing has been tested); once
    // validated, it holds learning ids - resolve those back to their
    // real statements so the UI always shows readable text either way.
    unresolvedUncertainties: memory.unresolved_uncertainties.map((entry) => {
      const asLearning = learnings.find((l) => l.learning_id === entry);
      return asLearning ? asLearning.statement : entry;
    }),
    experimentCount: memory.experiment_ids.length,
    criticalAssumptionCount: memory.critical_assumption_ids.length,
    criticalThresholdCount: memory.critical_threshold_ids.length,
    criticalRegretScenarioCount: memory.critical_regret_scenario_ids.length,
  };
}

/** Builds the visual "Decision Created -> ... -> Learning Recorded"
 * timeline from real timestamps already present on the decision's own
 * analysis run, experiments, and re-evaluations - never a fabricated
 * step. Steps that never happened (e.g. no experiment run yet) simply
 * don't appear, rather than being shown as pending/skipped placeholders. */
export function buildMemoryTimeline(
  decisionCreatedAt: string,
  response: ApiDecisionMemoryResponse,
): MemoryTimelineEvent[] {
  const events: MemoryTimelineEvent[] = [
    {
      id: 'decision-created',
      label: 'Decision created',
      detail: 'The decision was recorded and is ready for analysis.',
      timestampLabel: formatRelative(decisionCreatedAt),
      tone: 'neutral',
      sortKey: decisionCreatedAt,
    },
  ];

  if (response.memory) {
    events.push({
      id: 'analysis-completed',
      label: 'Analysis completed',
      detail: response.memory.original_assessment ?? 'The analysis pipeline produced its report.',
      timestampLabel: formatRelative(response.memory.created_at),
      tone: 'accent',
      sortKey: response.memory.created_at,
    });

    if (response.memory.critical_threshold_ids.length > 0) {
      events.push({
        id: 'threshold-identified',
        label: 'Critical threshold identified',
        detail: `${response.memory.critical_threshold_ids.length} threshold(s) recorded as the decision's breaking condition(s).`,
        timestampLabel: formatRelative(response.memory.created_at),
        tone: 'warning',
        sortKey: response.memory.created_at,
      });
    }
  }

  for (const experiment of response.experiments) {
    events.push({
      id: `experiment-started-${experiment.id}`,
      label: 'Experiment started',
      detail: experiment.title,
      timestampLabel: formatRelative(experiment.created_at),
      tone: 'info',
      sortKey: experiment.created_at,
    });
  }

  for (const assessment of response.assessments) {
    events.push({
      id: `experiment-completed-${assessment.experiment_id}`,
      label: 'Experiment completed',
      detail: "The experiment's observed result was submitted.",
      timestampLabel: formatRelative(assessment.created_at),
      tone: 'info',
      sortKey: assessment.created_at,
    });
    events.push({
      id: `reevaluated-${assessment.id}`,
      label: 'Decision re-evaluated',
      detail: assessment.decision_assessment.summary,
      timestampLabel: formatRelative(assessment.created_at),
      tone:
        assessment.decision_assessment.status === 'strengthened'
          ? 'success'
          : assessment.decision_assessment.status === 'weakened'
            ? 'danger'
            : 'neutral',
      sortKey: assessment.created_at,
    });
    events.push({
      id: `learning-recorded-${assessment.id}`,
      label: 'Learning recorded',
      detail: assessment.key_learning,
      timestampLabel: formatRelative(assessment.created_at),
      tone: 'accent',
      sortKey: assessment.created_at,
    });
  }

  return events.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
}
