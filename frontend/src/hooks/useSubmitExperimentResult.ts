import { useCallback, useState } from 'react';
import { experimentsApi } from '@/api';
import type { ApiExperimentResultCreate, ApiExperimentResultResponse } from '@/api/types';
import { describeApiError, isDuplicateSubmissionError } from '@/lib/apiError';

export interface SubmitExperimentResultState {
  isSubmitting: boolean;
  response: ApiExperimentResultResponse | null;
  error: { message: string; requestId: string | null; isDuplicate: boolean } | null;
}

export interface SubmitExperimentResult extends SubmitExperimentResultState {
  submit: (experimentId: string, payload: ApiExperimentResultCreate) => Promise<ApiExperimentResultResponse | null>;
  reset: () => void;
}

/**
 * Owns `POST /experiments/{id}/results` submission state, including the
 * backend's duplicate-submission protection: a 409 response
 * (`"This experiment already has a submitted result and cannot be
 * completed again."`) is surfaced as a clear, specific message - never a
 * raw API error - per the backend's own standardized error envelope.
 */
export function useSubmitExperimentResult(): SubmitExperimentResult {
  const [state, setState] = useState<SubmitExperimentResultState>({
    isSubmitting: false,
    response: null,
    error: null,
  });

  const submit = useCallback(
    async (experimentId: string, payload: ApiExperimentResultCreate) => {
      setState({ isSubmitting: true, response: null, error: null });
      try {
        const response = await experimentsApi.submitExperimentResult(experimentId, payload);
        setState({ isSubmitting: false, response, error: null });
        return response;
      } catch (error) {
        const described = describeApiError(error);
        const duplicate = isDuplicateSubmissionError(error);
        setState({
          isSubmitting: false,
          response: null,
          error: {
            message: duplicate
              ? 'Results for this experiment have already been submitted.'
              : described.message,
            requestId: described.requestId,
            isDuplicate: duplicate,
          },
        });
        return null;
      }
    },
    [],
  );

  const reset = useCallback(() => setState({ isSubmitting: false, response: null, error: null }), []);

  return { ...state, submit, reset };
}
