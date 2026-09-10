import { vi } from 'vitest';

export interface MockResponseSpec {
  status?: number;
  body?: unknown;
  headers?: Record<string, string>;
}

/**
 * Installs a mock `global.fetch` for one test. Never makes a real network
 * request - every test using this must not reach a real backend, AWS
 * service, or Bedrock/DynamoDB endpoint.
 */
export function mockFetchOnce(spec: MockResponseSpec): ReturnType<typeof vi.fn> {
  const { status = 200, body = {}, headers = {} } = spec;
  const mock = vi.fn().mockResolvedValue(
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'test-request-id', ...headers },
    }),
  );
  vi.stubGlobal('fetch', mock);
  return mock;
}

export function mockFetchSequence(specs: MockResponseSpec[]): ReturnType<typeof vi.fn> {
  const mock = vi.fn();
  for (const spec of specs) {
    const { status = 200, body = {}, headers = {} } = spec;
    mock.mockResolvedValueOnce(
      new Response(status === 204 ? null : JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'test-request-id', ...headers },
      }),
    );
  }
  vi.stubGlobal('fetch', mock);
  return mock;
}
