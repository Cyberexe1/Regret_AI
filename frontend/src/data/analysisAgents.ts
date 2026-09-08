import {
  EyeOff,
  FileSearch,
  FlaskConical,
  GitBranch,
  Layers,
  ScanSearch,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react';
import type { Tone } from '@/types';

/* -------------------------------------------------------------------------- *
 * Simulated stress test.
 *
 * There is no engine behind this yet. The sequence below is a local, timed
 * script: it shows which specialist is working and what it concluded, and
 * deliberately shows no model reasoning.
 * -------------------------------------------------------------------------- */

export type AgentStatus = 'waiting' | 'running' | 'complete';

export interface AnalysisAgent {
  id: string;
  index: string;
  name: string;
  description: string;
  icon: LucideIcon;
}

export const analysisAgents: AnalysisAgent[] = [
  {
    id: 'decision-analyzer',
    index: '01',
    name: 'Decision Analyzer',
    description: 'Reconstructs what is actually being committed to, and in what shape.',
    icon: ScanSearch,
  },
  {
    id: 'assumption-hunter',
    index: '02',
    name: 'Assumption Hunter',
    description: 'Separates stated reasoning from what is being taken for granted.',
    icon: Layers,
  },
  {
    id: 'blindspot-hunter',
    index: '03',
    name: 'Blindspot Hunter',
    description: 'Looks for the categories missing from the framing entirely.',
    icon: EyeOff,
  },
  {
    id: 'evidence-agent',
    index: '04',
    name: 'Evidence Agent',
    description: 'Weighs what backs each assumption and flags the unsupported ones.',
    icon: FileSearch,
  },
  {
    id: 'devils-advocate',
    index: '05',
    name: "Devil's Advocate",
    description: 'Argues against the decision on purpose, attacking the framing itself.',
    icon: ShieldAlert,
  },
  {
    id: 'regret-simulator',
    index: '06',
    name: 'Regret Simulator',
    description: 'Projects how this reads back at six months, one year and five years.',
    icon: GitBranch,
  },
  {
    id: 'experiment-planner',
    index: '07',
    name: 'Experiment Planner',
    description: 'Finds the cheapest test that would genuinely change your mind.',
    icon: FlaskConical,
  },
];

/* --- Timeline ------------------------------------------------------------- */

export interface AnalysisStage {
  /** Agent running during this stage. */
  agentId: string;
  /** Progress percentage when the stage begins. */
  startProgress: number;
  durationMs: number;
}

/**
 * Checkpoints match the brief: 0, 15, 30, 50, 65, 80, 95, 100.
 * Durations total roughly 16.6s, inside the 15-20s target.
 */
export const analysisStages: AnalysisStage[] = [
  { agentId: 'decision-analyzer', startProgress: 0, durationMs: 2200 },
  { agentId: 'assumption-hunter', startProgress: 15, durationMs: 2400 },
  { agentId: 'blindspot-hunter', startProgress: 30, durationMs: 2800 },
  { agentId: 'evidence-agent', startProgress: 50, durationMs: 2600 },
  { agentId: 'devils-advocate', startProgress: 65, durationMs: 2400 },
  { agentId: 'regret-simulator', startProgress: 80, durationMs: 2400 },
  { agentId: 'experiment-planner', startProgress: 95, durationMs: 1800 },
];

export const analysisDurationMs = analysisStages.reduce(
  (total, stage) => total + stage.durationMs,
  0,
);

/* --- Findings ------------------------------------------------------------- */

export interface AnalysisFinding {
  id: string;
  /** Which specialist produced it. */
  agentId: string;
  headline: string;
  tone: Tone;
  /** Revealed once analysis progress passes this mark. */
  atProgress: number;
}

/** Conclusions only. No intermediate reasoning is shown. */
export const analysisFindings: AnalysisFinding[] = [
  {
    id: 'fnd-1',
    agentId: 'decision-analyzer',
    headline: 'Framed as a single upfront commitment with no staged alternative',
    tone: 'info',
    atProgress: 12,
  },
  {
    id: 'fnd-2',
    agentId: 'assumption-hunter',
    headline: 'Found 7 implicit assumptions',
    tone: 'accent',
    atProgress: 27,
  },
  {
    id: 'fnd-3',
    agentId: 'blindspot-hunter',
    headline: 'Repeat customer behavior may be a critical uncertainty',
    tone: 'warning',
    atProgress: 46,
  },
  {
    id: 'fnd-4',
    agentId: 'evidence-agent',
    headline: '3 assumptions lack supporting evidence',
    tone: 'warning',
    atProgress: 62,
  },
  {
    id: 'fnd-5',
    agentId: 'devils-advocate',
    headline: 'Platform commission assumptions require validation',
    tone: 'warning',
    atProgress: 77,
  },
  {
    id: 'fnd-6',
    agentId: 'regret-simulator',
    headline: 'One potential failure threshold identified',
    tone: 'danger',
    atProgress: 92,
  },
  {
    id: 'fnd-7',
    agentId: 'experiment-planner',
    headline: 'A decisive test exists at a fraction of the commitment',
    tone: 'success',
    atProgress: 99,
  },
];

/* --- Secondary metrics ---------------------------------------------------- */

export interface AnalysisMetricSpec {
  id: string;
  label: string;
  /** Value the counter settles on. */
  finalValue: number;
  /** Suffix rendered after the value, e.g. "sources". */
  unit?: string;
  /** Progress mark at which the counter reaches its final value. */
  settlesAtProgress: number;
  tone: Tone;
}

export const analysisMetricSpecs: AnalysisMetricSpec[] = [
  {
    id: 'evidence',
    label: 'Evidence checked',
    finalValue: 24,
    unit: 'sources',
    settlesAtProgress: 65,
    tone: 'neutral',
  },
  {
    id: 'assumptions',
    label: 'Assumptions',
    finalValue: 7,
    settlesAtProgress: 30,
    tone: 'accent',
  },
  {
    id: 'blindspots',
    label: 'Blindspots',
    finalValue: 4,
    settlesAtProgress: 50,
    tone: 'warning',
  },
  {
    id: 'uncertainties',
    label: 'Critical uncertainties',
    finalValue: 2,
    settlesAtProgress: 80,
    tone: 'danger',
  },
];

/** Shown when no draft was carried over from intake. */
export const fallbackDecisionStatement =
  'Should I invest ₹5,00,000 to start a cloud kitchen?';
