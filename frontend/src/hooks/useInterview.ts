import { useCallback, useRef, useState } from 'react';
import { interviewApi } from '@/api';
import type {
  ApiDecisionInterviewState,
  ApiDecisionSnapshot,
  InterviewReadinessLevel,
} from '@/api/types';
import { describeApiError } from '@/lib/apiError';

export type InterviewStage =
  | 'idle'
  | 'starting'
  | 'awaiting-answer'
  | 'submitting'
  | 'ready'
  | 'completing'
  | 'completed';

export interface InterviewMessage {
  id: string;
  role: 'user' | 'regret';
  text: string;
}

export interface InterviewState {
  stage: InterviewStage;
  interviewId: string | null;
  state: ApiDecisionInterviewState | null;
  messages: InterviewMessage[];
  currentQuestion: string | null;
  readiness: InterviewReadinessLevel | null;
  suggestedChips: string[];
  snapshot: ApiDecisionSnapshot | null;
  /** False only when the most recent turn's Interview Agent call
   * failed and a deterministic fallback question was used instead
   * (spec section 28) - the UI shows a small, non-blocking notice, and
   * the user can always continue with what's already been collected. */
  agentAvailable: boolean;
  error: { message: string; requestId: string | null } | null;
}

const INITIAL_STATE: InterviewState = {
  stage: 'idle',
  interviewId: null,
  state: null,
  messages: [],
  currentQuestion: null,
  readiness: null,
  suggestedChips: [],
  snapshot: null,
  agentAvailable: true,
  error: null,
};

let messageSequence = 0;
function nextMessageId(): string {
  messageSequence += 1;
  return `msg-${Date.now().toString(36)}-${messageSequence}`;
}

/**
 * Owns the full Adaptive Decision Interview conversation lifecycle
 * (REGRET ENGINE 2.0, Step 27) - start, respond, complete, skip. Kept
 * as its own hook (mirrors `useDecisionSubmission`'s own separation of
 * network/state concerns from form state) so the Interview Console
 * component stays purely presentational.
 *
 * Every network call is tracked via `expected_turn_number` so a dropped
 * response and a client retry can never be double-processed - see
 * `api/interview.ts`'s own docstring.
 */
export function useInterview() {
  const [state, setState] = useState<InterviewState>(INITIAL_STATE);
  const lastTurnNumberRef = useRef(0);

  const start = useCallback(async (decisionId: string, selectedCategories: string[]) => {
    setState((current) => ({ ...current, stage: 'starting', error: null }));
    try {
      const response = await interviewApi.startInterview(decisionId, {
        selected_categories: selectedCategories,
      });
      lastTurnNumberRef.current = response.state.turn_number;
      setState({
        ...INITIAL_STATE,
        stage: 'awaiting-answer',
        interviewId: response.interview_id,
        state: response.state,
        currentQuestion: response.first_question,
        readiness: response.state.readiness,
        messages: [{ id: nextMessageId(), role: 'regret', text: response.first_question }],
      });
      return response.interview_id;
    } catch (error) {
      setState((current) => ({ ...current, stage: 'idle', error: describeApiError(error) }));
      return null;
    }
  }, []);

  const respond = useCallback(
    async (message: string) => {
      if (!state.interviewId) return;
      const trimmed = message.trim();
      if (!trimmed) return;

      const userMessageId = nextMessageId();
      setState((current) => ({
        ...current,
        stage: 'submitting',
        error: null,
        messages: [...current.messages, { id: userMessageId, role: 'user', text: trimmed }],
      }));

      try {
        const response = await interviewApi.respondToInterview(state.interviewId, {
          message: trimmed,
          expected_turn_number: lastTurnNumberRef.current,
        });
        lastTurnNumberRef.current = response.current_state.turn_number;

        setState((current) => ({
          ...current,
          stage: response.next_question ? 'awaiting-answer' : 'ready',
          state: response.current_state,
          currentQuestion: response.next_question,
          readiness: response.readiness,
          suggestedChips: response.suggested_chips,
          agentAvailable: response.agent_available,
          messages: response.response
            ? [...current.messages, { id: nextMessageId(), role: 'regret', text: response.response }]
            : current.messages,
        }));
      } catch (error) {
        setState((current) => ({
          ...current,
          stage: 'awaiting-answer',
          error: describeApiError(error),
        }));
      }
    },
    [state.interviewId],
  );

  const complete = useCallback(async () => {
    if (!state.interviewId) return null;
    setState((current) => ({ ...current, stage: 'completing', error: null }));
    try {
      const response = await interviewApi.completeInterview(state.interviewId);
      setState((current) => ({ ...current, stage: 'completed', snapshot: response.snapshot }));
      return response.snapshot;
    } catch (error) {
      setState((current) => ({ ...current, stage: 'ready', error: describeApiError(error) }));
      return null;
    }
  }, [state.interviewId]);

  const skip = useCallback(async () => {
    if (!state.interviewId) return null;
    setState((current) => ({ ...current, stage: 'completing', error: null }));
    try {
      const response = await interviewApi.skipInterview(state.interviewId);
      setState((current) => ({ ...current, stage: 'completed', snapshot: response.snapshot }));
      return response.snapshot;
    } catch (error) {
      setState((current) => ({ ...current, stage: 'awaiting-answer', error: describeApiError(error) }));
      return null;
    }
  }, [state.interviewId]);

  const reset = useCallback(() => {
    lastTurnNumberRef.current = 0;
    setState(INITIAL_STATE);
  }, []);

  return { ...state, start, respond, complete, skip, reset };
}
