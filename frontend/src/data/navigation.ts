import { FlaskConical, History, LayoutDashboard, Settings, SquarePen } from 'lucide-react';
import type { NavItem } from '@/types';

/** Single source of truth for every path in the app. */
export const ROUTES = {
  landing: '/',
  dashboard: '/dashboard',
  newDecision: '/decisions/new',
  decisions: '/decisions',
  analysis: '/analysis',
  decisionDetail: '/decision/:id',
  decisionGraph: '/decision/:id/graph',
  experiments: '/experiments',
  settings: '/settings',
} as const;

export function decisionPath(id: string): string {
  return `/decision/${id}`;
}

export function decisionGraphPath(id: string): string {
  return `/decision/${id}/graph`;
}

/** Sidebar navigation, in the order a user moves through the product. */
export const primaryNav: NavItem[] = [
  { label: 'Dashboard', to: ROUTES.dashboard, icon: LayoutDashboard },
  { label: 'New Decision', to: ROUTES.newDecision, icon: SquarePen, emphasis: true },
  { label: 'Decision History', to: ROUTES.decisions, icon: History },
  { label: 'Experiments', to: ROUTES.experiments, icon: FlaskConical },
  { label: 'Settings', to: ROUTES.settings, icon: Settings },
];

export interface RouteMeta {
  path: string;
  /** Shown as the topbar heading. */
  title: string;
  /** Small uppercase label above the heading. */
  eyebrow: string;
}

/**
 * Ordered most-specific first so `matchPath` resolves `/decisions/new`
 * before `/decisions`.
 */
export const routeMeta: RouteMeta[] = [
  { path: ROUTES.newDecision, title: 'New Decision', eyebrow: 'Intake' },
  { path: ROUTES.decisions, title: 'Decision History', eyebrow: 'Archive' },
  { path: ROUTES.decisionGraph, title: 'Dependency Graph', eyebrow: 'Decision' },
  { path: ROUTES.decisionDetail, title: 'Decision Report', eyebrow: 'Decision' },
  { path: ROUTES.analysis, title: 'Analysis Workspace', eyebrow: 'Engine' },
  { path: ROUTES.experiments, title: 'Experiments', eyebrow: 'Validation' },
  { path: ROUTES.settings, title: 'Settings', eyebrow: 'Workspace' },
  { path: ROUTES.dashboard, title: 'Dashboard', eyebrow: 'Overview' },
];
