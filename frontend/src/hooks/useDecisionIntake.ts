import { useCallback, useMemo, useState } from 'react';
import { resolveIntakeSteps, type ResolvedIntakeStep } from '@/data/intake';
import { emptyDecisionDraft } from '@/lib/decisionDraft';
import type { DecisionDraft } from '@/types';
import { useEvidenceFiles, type DraftEvidenceFileWithBlob } from './useEvidenceFiles';

type IntakeForm = Omit<DecisionDraft, 'evidence'>;
type ConstraintKey = keyof DecisionDraft['constraints'];
type TextFieldKey =
  | 'decision'
  | 'desiredOutcome'
  | 'constraintsText'
  | 'beliefs'
  | 'uncertainties'
  | 'commitment'
  | 'alternatives'
  | 'sourceUrl';

/** Same shape as `DecisionDraft`, but `evidence` keeps the real `File`
 * blobs so submission can actually upload them. */
export type DecisionDraftWithFiles = Omit<DecisionDraft, 'evidence'> & {
  evidence: DraftEvidenceFileWithBlob[];
};

const { evidence: _ignoredEvidence, ...emptyForm } = emptyDecisionDraft;

export interface DecisionIntake {
  draft: DecisionDraftWithFiles;
  steps: ResolvedIntakeStep[];
  /** The decision statement is the only hard requirement. */
  canSubmit: boolean;
  /** Rejection messages from the last attempt to attach files. */
  evidenceErrors: string[];
  setField: (key: TextFieldKey, value: string) => void;
  setCategories: (categories: DecisionDraft['categories']) => void;
  setConstraint: <K extends ConstraintKey>(
    key: K,
    value: DecisionDraft['constraints'][K],
  ) => void;
  /** One category-specific "note" chip's free-text value, keyed by the
   * chip's own stable id - see `@/data/decisionTypes`'s `ContextChip`. */
  setExtraDetail: (id: string, value: string) => void;
  /** Replaces the entire form in one shot - used by "Try an example". */
  applyExample: (example: Partial<IntakeForm>) => void;
  addFiles: (files: File[]) => void;
  removeFile: (id: string) => void;
}

/**
 * Owns intake form state and the rules around it, so the page and its sections
 * stay presentational. Attachment handling is delegated to `useEvidenceFiles`.
 */
export function useDecisionIntake(): DecisionIntake {
  const [form, setForm] = useState<IntakeForm>(emptyForm);
  const evidence = useEvidenceFiles();

  const setField = useCallback((key: TextFieldKey, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  }, []);

  const setCategories = useCallback((categories: DecisionDraft['categories']) => {
    setForm((current) => ({ ...current, categories }));
  }, []);

  const setConstraint = useCallback<DecisionIntake['setConstraint']>((key, value) => {
    setForm((current) => ({
      ...current,
      constraints: { ...current.constraints, [key]: value },
    }));
  }, []);

  const setExtraDetail = useCallback((id: string, value: string) => {
    setForm((current) => ({
      ...current,
      extraDetails: { ...current.extraDetails, [id]: value },
    }));
  }, []);

  const applyExample = useCallback((example: Partial<IntakeForm>) => {
    setForm((current) => ({ ...current, ...example }));
  }, []);

  const draft = useMemo<DecisionDraftWithFiles>(
    () => ({ ...form, evidence: evidence.files }),
    [form, evidence.files],
  );

  const steps = useMemo(() => resolveIntakeSteps(draft), [draft]);

  return {
    draft,
    steps,
    canSubmit: draft.decision.trim().length > 0,
    evidenceErrors: evidence.errors,
    setField,
    setCategories,
    setConstraint,
    setExtraDetail,
    applyExample,
    addFiles: evidence.addFiles,
    removeFile: evidence.removeFile,
  };
}
