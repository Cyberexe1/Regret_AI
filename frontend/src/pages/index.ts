export { LandingPage } from './LandingPage';
export { NotFoundPage } from './NotFoundPage';

// Workspace pages are intentionally absent. `App.tsx` imports them with
// `lazy(() => import(...))`, and re-exporting them here would statically pull
// every page back into the main chunk.
