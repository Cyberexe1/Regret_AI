import {
  CircleQuestionMark,
  FileText,
  FlaskConical,
  RefreshCw,
  ScanSearch,
  ShieldAlert,
  SquarePen,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react';
import type { RiskLevel, Tone } from '@/types';

/* -------------------------------------------------------------------------- *
 * Dashboard sample data.
 *
 * Static and local. Counts here are internally consistent: the portfolio
 * breakdown sums to the number of analysed decisions, and the high-risk band
 * matches the high-risk metric.
 * -------------------------------------------------------------------------- */

export interface DashboardMetric {
  label: string;
  value: number;
  icon: LucideIcon;
  tone: Tone;
  /** Explains how the figure is derived, shown on hover. */
  help: string;
}

export const dashboardMetrics: DashboardMetric[] = [
  {
    label: 'Decisions analyzed',
    value: 12,
    icon: ScanSearch,
    tone: 'neutral',
    help: 'Decisions that have completed at least one full analysis pass.',
  },
  {
    label: 'High-risk decisions',
    value: 3,
    icon: TriangleAlert,
    tone: 'danger',
    help: 'Regret index above 70, or irreversible with an untested critical assumption.',
  },
  {
    label: 'Open experiments',
    value: 4,
    icon: FlaskConical,
    tone: 'info',
    help: 'Experiments currently running against an unresolved assumption.',
  },
  {
    label: 'Unresolved uncertainties',
    value: 7,
    icon: CircleQuestionMark,
    tone: 'warning',
    help: 'Critical assumptions with no evidence strong enough to settle them.',
  },
];

/* --- Recent decisions ----------------------------------------------------- */

/** Recommendation state, distinct from a decision's lifecycle status. */
export interface DecisionSignal {
  label: string;
  tone: Tone;
}

export interface RecentDecisionRow {
  /** Matches an id in `data/decisions.ts`, so the row links somewhere real. */
  id: string;
  title: string;
  risk: RiskLevel;
  signal: DecisionSignal;
  updatedLabel: string;
}

export const recentDecisions: RecentDecisionRow[] = [
  {
    id: 'dcn-5104',
    title: 'Start a cloud kitchen',
    risk: 'medium',
    signal: { label: 'Experiment recommended', tone: 'accent' },
    updatedLabel: 'Today',
  },
  {
    id: 'dcn-5098',
    title: 'Buy a new laptop',
    risk: 'low',
    signal: { label: 'Decision ready', tone: 'success' },
    updatedLabel: 'Yesterday',
  },
  {
    id: 'dcn-5091',
    title: 'Leave job for GATE preparation',
    risk: 'high',
    signal: { label: 'Evidence incomplete', tone: 'warning' },
    updatedLabel: '3 days ago',
  },
];

/* --- Portfolio breakdown -------------------------------------------------- */

export interface PortfolioBand {
  risk: RiskLevel;
  label: string;
  count: number;
}

/** Sums to 12, matching "Decisions analyzed". */
export const portfolioBands: PortfolioBand[] = [
  { risk: 'low', label: 'Low risk', count: 5 },
  { risk: 'medium', label: 'Medium risk', count: 4 },
  { risk: 'high', label: 'High risk', count: 3 },
];

/* --- Open experiments ----------------------------------------------------- */

export interface ExperimentProgressRow {
  /** Matches an id in `data/experiments.ts`. */
  id: string;
  title: string;
  /** 0-100 elapsed against the planned window. */
  progress: number;
  daysRemaining: number;
  signal: DecisionSignal;
}

export const openExperiments: ExperimentProgressRow[] = [
  {
    id: 'exp-2210',
    title: '14-day customer retention pilot',
    progress: 65,
    daysRemaining: 4,
    signal: { label: 'Collecting evidence', tone: 'info' },
  },
  {
    id: 'exp-2211',
    title: 'Cloud kitchen demand test',
    progress: 30,
    daysRemaining: 11,
    signal: { label: 'Early', tone: 'neutral' },
  },
];

/** Total running, of which the card shows the two closest to completion. */
export const openExperimentTotal = 4;

/* --- Headline uncertainty ------------------------------------------------- */

export interface TopUncertainty {
  title: string;
  detail: string;
  affectedDecisions: number;
}

export const topUncertainty: TopUncertainty = {
  title: 'Repeat customer behavior',
  detail: '3 of your recent decisions depend on assumptions about repeat usage.',
  affectedDecisions: 3,
};

/* --- Activity ------------------------------------------------------------- */

export interface ActivityEvent {
  id: string;
  icon: LucideIcon;
  label: string;
  detail: string;
  timestamp: string;
  tone: Tone;
}

export const activityEvents: ActivityEvent[] = [
  {
    id: 'act-1',
    icon: RefreshCw,
    label: 'Decision re-evaluated',
    detail: 'Start a cloud kitchen — regret index moved from 61 to 54',
    timestamp: 'Today, 11:20',
    tone: 'accent',
  },
  {
    id: 'act-2',
    icon: FlaskConical,
    label: 'Experiment started',
    detail: '14-day customer retention pilot',
    timestamp: 'Today, 08:05',
    tone: 'info',
  },
  {
    id: 'act-3',
    icon: ShieldAlert,
    label: 'Assumption challenged',
    detail: 'Repeat rate of 24% rests on category benchmarks, not observed orders',
    timestamp: 'Yesterday, 17:42',
    tone: 'warning',
  },
  {
    id: 'act-4',
    icon: FileText,
    label: 'Evidence added',
    detail: 'Aggregator commission schedule attached to Start a cloud kitchen',
    timestamp: 'Yesterday, 10:16',
    tone: 'neutral',
  },
  {
    id: 'act-5',
    icon: SquarePen,
    label: 'Decision created',
    detail: 'Leave job for GATE preparation',
    timestamp: '3 days ago, 09:30',
    tone: 'neutral',
  },
];
