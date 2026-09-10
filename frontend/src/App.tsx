import { lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { ROUTES } from '@/data/navigation';
import { LandingPage } from '@/pages/LandingPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

/**
 * Workspace routes load on demand, so a visitor landing on `/` does not
 * download the dashboard, intake form and report. `AppShell` provides the
 * Suspense boundary, keeping sidebar and topbar visible while a module arrives.
 */
const DashboardPage = lazy(async () => ({
  default: (await import('@/pages/DashboardPage')).DashboardPage,
}));
const NewDecisionPage = lazy(async () => ({
  default: (await import('@/pages/NewDecisionPage')).NewDecisionPage,
}));
const DecisionHistoryPage = lazy(async () => ({
  default: (await import('@/pages/DecisionHistoryPage')).DecisionHistoryPage,
}));
const AnalysisPage = lazy(async () => ({
  default: (await import('@/pages/AnalysisPage')).AnalysisPage,
}));
const DecisionDetailPage = lazy(async () => ({
  default: (await import('@/pages/DecisionDetailPage')).DecisionDetailPage,
}));
const DecisionGraphPage = lazy(async () => ({
  default: (await import('@/pages/DecisionGraphPage')).DecisionGraphPage,
}));
const ExperimentsPage = lazy(async () => ({
  default: (await import('@/pages/ExperimentsPage')).ExperimentsPage,
}));
const SettingsPage = lazy(async () => ({
  default: (await import('@/pages/SettingsPage')).SettingsPage,
}));

export function App() {
  return (
    <Routes>
      {/* Public shell-free route */}
      <Route path={ROUTES.landing} element={<LandingPage />} />

      {/* Everything inside the product chrome */}
      <Route element={<AppShell />}>
        <Route path={ROUTES.dashboard} element={<DashboardPage />} />
        <Route path={ROUTES.newDecision} element={<NewDecisionPage />} />
        <Route path={ROUTES.decisions} element={<DecisionHistoryPage />} />
        <Route path={ROUTES.analysis} element={<AnalysisPage />} />
        <Route path={ROUTES.decisionDetail} element={<DecisionDetailPage />} />
        <Route path={ROUTES.decisionGraph} element={<DecisionGraphPage />} />
        <Route path={ROUTES.experiments} element={<ExperimentsPage />} />
        <Route path={ROUTES.experimentDetail} element={<ExperimentsPage />} />
        <Route path={ROUTES.settings} element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
