import {
  EyeOff,
  FileSearch,
  FlaskConical,
  Gauge,
  GitBranch,
  Globe,
  Layers,
  ScanSearch,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react';
import { ANALYSIS_STAGE_IDS, type AnalysisStageId } from '@/api/types';

/* -------------------------------------------------------------------------- *
 * Real analysis pipeline metadata.
 *
 * These 9 stage ids match the backend's `AnalysisRunStatusResponse.stage_statuses`
 * keys exactly (see app/agents/orchestrator.py). Only presentational fields
 * (name/description/icon) are authored here - status, ordering-in-progress,
 * and completion are always driven by the real backend response, never
 * simulated locally.
 * -------------------------------------------------------------------------- */

export interface AnalysisAgent {
  id: AnalysisStageId;
  index: string;
  name: string;
  description: string;
  icon: LucideIcon;
}

const AGENT_META: Record<AnalysisStageId, Omit<AnalysisAgent, 'id' | 'index'>> = {
  decision_analyzer: {
    name: 'Decision Analyzer',
    description: 'Reconstructs what is actually being committed to, and in what shape.',
    icon: ScanSearch,
  },
  assumption_hunter: {
    name: 'Assumption Hunter',
    description: 'Separates stated reasoning from what is being taken for granted.',
    icon: Layers,
  },
  blindspot_hunter: {
    name: 'Blindspot Hunter',
    description: 'Looks for the categories missing from the framing entirely.',
    icon: EyeOff,
  },
  research_agent: {
    name: 'Research Agent',
    description: 'Looks for external evidence on the decision\u2019s most critical uncertainties.',
    icon: Globe,
  },
  evidence_agent: {
    name: 'Evidence Agent',
    description: 'Weighs what backs each assumption and flags the unsupported ones.',
    icon: FileSearch,
  },
  devils_advocate: {
    name: "Devil's Advocate",
    description: 'Argues against the decision on purpose, attacking the framing itself.',
    icon: ShieldAlert,
  },
  regret_simulator: {
    name: 'Regret Simulator',
    description: 'Projects the conditions under which this decision is regretted.',
    icon: GitBranch,
  },
  threshold_engine: {
    name: 'Threshold Engine',
    description: 'Identifies the tipping points that decide whether this decision holds.',
    icon: Gauge,
  },
  experiment_planner: {
    name: 'Experiment Planner',
    description: 'Finds the cheapest test that would genuinely change your mind.',
    icon: FlaskConical,
  },
};

export const analysisAgents: AnalysisAgent[] = ANALYSIS_STAGE_IDS.map((id, index) => ({
  id,
  index: String(index + 1).padStart(2, '0'),
  ...AGENT_META[id],
}));

/** Shown while the decision statement itself is still loading. */
export const fallbackDecisionStatement = 'Loading your decision\u2026';
