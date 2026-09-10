import { ApiError } from '@/api/client';

/**
 * Human-readable message for any error surfaced by the API client. Always
 * shows the backend's own `error.message` (never a stack trace or raw
 * exception string), and appends the request id when one exists so a user
 * can cite it if they report an issue - see `app.core.errors` on the
 * backend for the envelope this reads.
 */
export function describeApiError(error: unknown): { message: string; requestId: string | null } {
  if (error instanceof ApiError) {
    return { message: error.message, requestId: error.requestId };
  }
  if (error instanceof Error) {
    return { message: error.message, requestId: null };
  }
  return { message: 'Something unexpected went wrong.', requestId: null };
}

/** True for the specific "this experiment already has a submitted result" conflict. */
export function isDuplicateSubmissionError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}

export function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
