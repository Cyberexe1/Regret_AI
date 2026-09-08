import { useCallback, useMemo, useState } from 'react';
import {
  maxEvidenceFileBytes,
  resolveIntakeSteps,
  supportedEvidenceExtensions,
  type ResolvedIntakeStep,
} from '@/data/intake';
import { emptyDecisionDraft } from '@/lib/decisionDraft';
import { formatFileSize } from '@/lib/format';
import type { DecisionDraft, DraftEvidenceFile } from '@/types';

let fileSequence = 0;

function nextFileId(): string {
  fileSequence += 1;
  return `evd-${Date.now().toString(36)}-${fileSequence}`;
}

function hasSupportedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return supportedEvidenceExtensions.some((extension) => lower.endsWith(extension));
}

type ConstraintKey = keyof DecisionDraft['constraints'];

export interface DecisionIntake {
  draft: DecisionDraft;
  steps: ResolvedIntakeStep[];
  /** The decision statement is the only hard requirement. */
  canSubmit: boolean;
  /** Rejection messages from the last attempt to attach files. */
  evidenceErrors: string[];
  setField: <K extends 'decision' | 'desiredOutcome' | 'beliefs' | 'sourceUrl'>(
    key: K,
    value: DecisionDraft[K],
  ) => void;
  setConstraint: <K extends ConstraintKey>(
    key: K,
    value: DecisionDraft['constraints'][K],
  ) => void;
  addFiles: (files: File[]) => void;
  removeFile: (id: string) => void;
}

/**
 * Owns intake form state and the rules around it, so the page and its sections
 * stay presentational.
 */
export function useDecisionIntake(): DecisionIntake {
  const [draft, setDraft] = useState<DecisionDraft>(emptyDecisionDraft);
  const [evidenceErrors, setEvidenceErrors] = useState<string[]>([]);

  const setField = useCallback<DecisionIntake['setField']>((key, value) => {
    setDraft((current) => ({ ...current, [key]: value }));
  }, []);

  const setConstraint = useCallback<DecisionIntake['setConstraint']>((key, value) => {
    setDraft((current) => ({
      ...current,
      constraints: { ...current.constraints, [key]: value },
    }));
  }, []);

  const addFiles = useCallback((files: File[]) => {
    const accepted: DraftEvidenceFile[] = [];
    const rejected: string[] = [];

    for (const file of files) {
      if (!hasSupportedExtension(file.name)) {
        rejected.push(`${file.name} is not a supported file type.`);
        continue;
      }
      if (file.size > maxEvidenceFileBytes) {
        rejected.push(
          `${file.name} is ${formatFileSize(file.size)}, over the ${formatFileSize(
            maxEvidenceFileBytes,
          )} limit.`,
        );
        continue;
      }
      accepted.push({
        id: nextFileId(),
        name: file.name,
        size: file.size,
        mimeType: file.type,
      });
    }

    setEvidenceErrors(rejected);

    if (accepted.length > 0) {
      setDraft((current) => ({ ...current, evidence: [...current.evidence, ...accepted] }));
    }
  }, []);

  const removeFile = useCallback((id: string) => {
    setDraft((current) => ({
      ...current,
      evidence: current.evidence.filter((file) => file.id !== id),
    }));
  }, []);

  const steps = useMemo(() => resolveIntakeSteps(draft), [draft]);
  const canSubmit = draft.decision.trim().length > 0;

  return {
    draft,
    steps,
    canSubmit,
    evidenceErrors,
    setField,
    setConstraint,
    addFiles,
    removeFile,
  };
}
