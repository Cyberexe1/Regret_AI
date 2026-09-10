/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the FastAPI backend's versioned API, e.g. http://localhost:8000/api/v1 */
  readonly VITE_API_BASE_URL?: string;
  /**
   * Development-only placeholder identity. The backend currently attributes
   * every request to a single fixed server-side user id regardless of what
   * the client sends, so this is not read by any request today - it exists
   * purely so a future auth header has one clearly-named place to read a
   * dev-mode override from, without scattering a literal string through the
   * app. See src/lib/devUser.ts.
   */
  readonly VITE_DEV_USER_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
