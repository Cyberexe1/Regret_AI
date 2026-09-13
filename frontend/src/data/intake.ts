import type { DecisionDraft, RiskTolerance } from '@/types';

/* -------------------------------------------------------------------------- *
 * Intake phases
 *
 * Four phases across one page. Section cards are tagged with the phase they
 * belong to, so the progress rail and the form cannot drift apart.
 * -------------------------------------------------------------------------- */

export const INTAKE_SECTION_IDS = {
  decision: 'intake-decision',
  context: 'intake-context',
  constraints: 'intake-constraints',
  beliefs: 'intake-beliefs',
  // REGRET ENGINE 2.0: "Relevant from your past decisions" - a live,
  // debounced preview, never part of the step-completion tracking above
  // (it has no bearing on whether the intake form itself is "done").
  historicalContext: 'intake-historical-context',
  evidence: 'intake-evidence',
  submit: 'intake-submit',
} as const;

export type IntakeStepStatus = 'complete' | 'current' | 'upcoming';

export interface IntakeStep {
  index: string;
  label: string;
  /** Section this step scrolls to. */
  target: string;
}

export const intakeSteps: IntakeStep[] = [
  { index: '01', label: 'Decision', target: INTAKE_SECTION_IDS.decision },
  { index: '02', label: 'Context', target: INTAKE_SECTION_IDS.context },
  { index: '03', label: 'Evidence', target: INTAKE_SECTION_IDS.evidence },
  { index: '04', label: 'Stress Test', target: INTAKE_SECTION_IDS.submit },
];

export interface ResolvedIntakeStep extends IntakeStep {
  status: IntakeStepStatus;
}

/**
 * Marks each phase complete from the draft itself. The stress test never
 * reports complete here: it only completes once it has actually been run.
 */
export function resolveIntakeSteps(draft: DecisionDraft): ResolvedIntakeStep[] {
  const completion = [
    draft.decision.trim().length > 0,
    draft.desiredOutcome.trim().length > 0 || draft.beliefs.trim().length > 0,
    draft.evidence.length > 0 || draft.sourceUrl.trim().length > 0,
    false,
  ];

  const currentIndex = completion.indexOf(false);

  return intakeSteps.map((step, index) => ({
    ...step,
    status: completion[index] ? 'complete' : index === currentIndex ? 'current' : 'upcoming',
  }));
}

/* --- Constraints ---------------------------------------------------------- */

export interface RiskToleranceOption {
  value: RiskTolerance;
  label: string;
  description: string;
}

export const riskToleranceOptions: RiskToleranceOption[] = [
  {
    value: 'conservative',
    label: 'Conservative',
    description: 'Protect the downside, even if it limits upside.',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    description: 'Accept measured risk when evidence supports it.',
  },
  {
    value: 'aggressive',
    label: 'Aggressive',
    description: 'Accept greater downside for a potentially larger upside.',
  },
];

/* --- Evidence ------------------------------------------------------------- */

/** Extensions the picker offers and the drop handler accepts. */
export const supportedEvidenceExtensions = [
  '.pdf',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.csv',
  '.txt',
  '.md',
  '.png',
  '.jpg',
  '.jpeg',
] as const;

export const supportedEvidenceLabel = 'PDF, DOC, XLS, CSV, TXT, MD, PNG, JPG';

/** Enforced in the browser, so the limit shown is a real one. */
export const maxEvidenceFileBytes = 25 * 1024 * 1024;
