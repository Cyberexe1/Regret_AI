import { useCallback, useState } from 'react';
import { decisionsApi, evidenceApi } from '@/api';
import { describeApiError } from '@/lib/apiError';
import { buildDecisionCreatePayload } from '@/lib/decisionPayload';
import type { DecisionDraftWithFiles } from './useDecisionIntake';

export type SubmissionStage = 'idle' | 'creating-decision' | 'uploading-evidence' | 'done' | 'error';

export interface EvidenceUploadOutcome {
  fileName: string;
  ok: boolean;
  message?: string;
}

export interface DecisionSubmissionState {
  stage: SubmissionStage;
  /** Real, server-assigned decision id once creation succeeds. */
  decisionId: string | null;
  /** Per-file upload outcome, so a failed upload never hides a succeeded one. */
  evidenceOutcomes: EvidenceUploadOutcome[];
  error: { message: string; requestId: string | null } | null;
}

export interface DecisionSubmission extends DecisionSubmissionState {
  /**
   * Creates the decision, then uploads every attached evidence file.
   * Returns the created decision id on success (even if some individual
   * evidence uploads failed - a failed upload never discards the decision
   * that was already created, per the intake flow's requirement).
   */
  submit: (draft: DecisionDraftWithFiles) => Promise<string | null>;
  reset: () => void;
}

/**
 * Owns the real create-decision + upload-evidence flow, kept as its own
 * hook (rather than folded into `useDecisionIntake`, which only owns form
 * state) so the network/submission concern and the form concern can be
 * tested and reasoned about separately.
 */
export function useDecisionSubmission(): DecisionSubmission {
  const [state, setState] = useState<DecisionSubmissionState>({
    stage: 'idle',
    decisionId: null,
    evidenceOutcomes: [],
    error: null,
  });

  const reset = useCallback(() => {
    setState({ stage: 'idle', decisionId: null, evidenceOutcomes: [], error: null });
  }, []);

  const submit = useCallback(async (draft: DecisionDraftWithFiles): Promise<string | null> => {
    setState({ stage: 'creating-decision', decisionId: null, evidenceOutcomes: [], error: null });

    let decisionId: string;
    try {
      const created = await decisionsApi.createDecision(buildDecisionCreatePayload(draft));
      decisionId = created.id;
    } catch (error) {
      setState({
        stage: 'error',
        decisionId: null,
        evidenceOutcomes: [],
        error: describeApiError(error),
      });
      return null;
    }

    setState((current) => ({ ...current, stage: 'uploading-evidence', decisionId }));

    // Uploaded sequentially and independently: one failed file must never
    // stop the others, and the decision itself is already created and
    // must never be lost because of an evidence upload failure.
    const outcomes: EvidenceUploadOutcome[] = [];
    for (const item of draft.evidence) {
      try {
        await evidenceApi.uploadEvidence(decisionId, item.file);
        outcomes.push({ fileName: item.name, ok: true });
      } catch (error) {
        outcomes.push({ fileName: item.name, ok: false, message: describeApiError(error).message });
      }
    }

    setState({ stage: 'done', decisionId, evidenceOutcomes: outcomes, error: null });
    return decisionId;
  }, []);

  return { ...state, submit, reset };
}
