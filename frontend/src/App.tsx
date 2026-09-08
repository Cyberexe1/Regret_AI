import { Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { ROUTES } from '@/data/navigation';
import {
  AnalysisPage,
  DashboardPage,
  DecisionDetailPage,
  DecisionHistoryPage,
  ExperimentsPage,
  LandingPage,
  NewDecisionPage,
  NotFoundPage,
  SettingsPage,
} from '@/pages';

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
        <Route path={ROUTES.experiments} element={<ExperimentsPage />} />
        <Route path={ROUTES.settings} element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
