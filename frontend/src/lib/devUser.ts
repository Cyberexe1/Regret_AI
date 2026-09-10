/**
 * Development-only identity placeholder.
 *
 * There is no authentication yet - the backend currently attributes every
 * request to a single fixed server-side user id
 * (`app.dependencies.auth.get_current_user_id`), regardless of what the
 * client sends. This module does NOT send anything to the backend today;
 * it exists solely as one clearly-named, isolated place to read a
 * dev-mode identity override from (`VITE_DEV_USER_ID`), so that when real
 * authentication is added later, only this one file needs to change to
 * start sending a real auth header - no dev user id is scattered through
 * the rest of the application.
 */
export function getDevUserId(): string | null {
  return import.meta.env.VITE_DEV_USER_ID ?? null;
}
