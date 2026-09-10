/**
 * Centralized HTTP client for the FastAPI backend.
 *
 * Every API module (`decisions.ts`, `evidence.ts`, `analysis.ts`,
 * `experiments.ts`, `research.ts`) goes through the functions here rather
 * than calling `fetch` directly, so retry-free error parsing, timeouts, and
 * the standardized error envelope are handled in exactly one place.
 *
 * Security: this file never reads or sends AWS/Bedrock/DynamoDB
 * credentials or API keys - the browser only ever talks to the FastAPI
 * base URL configured via `VITE_API_BASE_URL`.
 */

import type { ApiErrorBody } from './types';

const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1';
const DEFAULT_TIMEOUT_MS = 30_000;

function resolveBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return configured && configured.trim().length > 0 ? configured.trim() : DEFAULT_BASE_URL;
}

/** The backend's own base URL, exported for display (e.g. Settings page connection status). */
export const API_BASE_URL = resolveBaseUrl();

/**
 * Thrown for every non-2xx response and for network/timeout failures.
 * Carries the backend's own error code/request id when the response body
 * matched the standardized envelope, so callers can show a useful message
 * without ever displaying a stack trace.
 */
export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly requestId: string | null;
  /** True for network failures / timeouts - the request never reached the server. */
  readonly isNetworkError: boolean;

  constructor(options: {
    message: string;
    status: number | null;
    code: string;
    requestId: string | null;
    isNetworkError?: boolean;
  }) {
    super(options.message);
    this.name = 'ApiError';
    this.status = options.status;
    this.code = options.code;
    this.requestId = options.requestId;
    this.isNetworkError = options.isNetworkError ?? false;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.detail === 'string' &&
    typeof candidate.error === 'object' &&
    candidate.error !== null &&
    typeof (candidate.error as Record<string, unknown>).code === 'string'
  );
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Response wasn't JSON (e.g. an upstream proxy error page) - fall through.
  }

  if (isApiErrorBody(body)) {
    return new ApiError({
      message: body.error.message || body.detail,
      status: response.status,
      code: body.error.code,
      requestId: body.error.request_id,
    });
  }

  return new ApiError({
    message: `Request failed with status ${response.status}.`,
    status: response.status,
    code: 'UNKNOWN_ERROR',
    requestId: response.headers.get('X-Request-ID'),
  });
}

export interface RequestOptions {
  /** Query parameters appended to the URL. `undefined`/`null` values are omitted. */
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Aborts the request if it hasn't settled within this many ms. Defaults to 30s. */
  timeoutMs?: number;
  /** Lets a caller cancel the request from outside (e.g. on component unmount). */
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

/**
 * Combines a caller-supplied `AbortSignal` (e.g. from a component's cleanup
 * effect) with an internal timeout, so either one can cancel the request.
 */
function combineSignals(timeoutMs: number, external?: AbortSignal): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(new DOMException('Timeout', 'TimeoutError')), timeoutMs);

  const onExternalAbort = () => controller.abort(external?.reason);
  if (external) {
    if (external.aborted) controller.abort(external.reason);
    else external.addEventListener('abort', onExternalAbort);
  }

  return {
    signal: controller.signal,
    clear: () => {
      window.clearTimeout(timeoutId);
      external?.removeEventListener('abort', onExternalAbort);
    },
  };
}

async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  options: RequestOptions & { body?: unknown; isFormData?: boolean } = {},
): Promise<T> {
  const { query, timeoutMs = DEFAULT_TIMEOUT_MS, signal, body, isFormData } = options;
  const { signal: combinedSignal, clear } = combineSignals(timeoutMs, signal);

  const init: RequestInit = {
    method,
    signal: combinedSignal,
    headers: isFormData ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
  };

  try {
    const response = await fetch(buildUrl(path, query), init);

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;

    const isAbort = error instanceof DOMException && error.name === 'AbortError';
    const isTimeout = error instanceof DOMException && error.name === 'TimeoutError';

    if (isAbort && !isTimeout) {
      // A genuine caller-initiated cancellation (component unmount, navigation
      // away) - re-throw as-is so callers can distinguish it from a real
      // failure and choose not to show an error state for it.
      throw error;
    }

    throw new ApiError({
      message: isTimeout
        ? 'The request took too long to respond. The backend may be unavailable.'
        : 'Could not reach the backend. Check your connection and that the API is running.',
      status: null,
      code: isTimeout ? 'TIMEOUT' : 'NETWORK_ERROR',
      requestId: null,
      isNetworkError: true,
    });
  } finally {
    clear();
  }
}

export const apiClient = {
  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('GET', path, options);
  },
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('POST', path, { ...options, body });
  },
  postForm<T>(path: string, form: FormData, options?: RequestOptions): Promise<T> {
    return request<T>('POST', path, { ...options, body: form, isFormData: true });
  },
  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PATCH', path, { ...options, body });
  },
  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('DELETE', path, options);
  },
};

/** True if `error` represents the caller's own cancellation, not a failure. */
export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}
