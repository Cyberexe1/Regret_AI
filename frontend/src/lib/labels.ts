import type { AgentRunStatus, AnalysisRunStatus, DecisionStatus, ExperimentStatus } from '@/api/types';

/** Mirrors the backend's real `DecisionStatus` enum - see app/schemas/decision.py. */
export const statusLabel: Record<DecisionStatus, string> = {
  draft: 'Draft',
  queued: 'Queued',
  analyzing: 'Analyzing',
  completed: 'Analysis complete',
  needs_validation: 'Needs validation',
  archived: 'Archived',
};

/** Mirrors the backend's real `ExperimentStatus` enum - see app/schemas/decision_resources.py. */
export const experimentStatusLabel: Record<ExperimentStatus, string> = {
  recommended: 'Recommended',
  planned: 'Planned',
  active: 'Active',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

/** Mirrors the backend's real `AnalysisRunStatus` enum. */
export const analysisRunStatusLabel: Record<AnalysisRunStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Complete',
  failed: 'Failed',
};

/** Mirrors the backend's real per-stage `AgentRunStatus` enum. */
export const agentRunStatusLabel: Record<AgentRunStatus, string> = {
  pending: 'Waiting',
  running: 'Running',
  completed: 'Complete',
  failed: 'Failed',
  skipped: 'Skipped',
  unavailable: 'Unavailable',
};

/** Human names for the 9 real backend pipeline stage ids. */
export const stageLabel: Record<string, string> = {
  decision_analyzer: 'Decision Analyzer',
  assumption_hunter: 'Assumption Hunter',
  blindspot_hunter: 'Blindspot Hunter',
  research_agent: 'Research Agent',
  evidence_agent: 'Evidence Agent',
  devils_advocate: "Devil's Advocate",
  regret_simulator: 'Regret Simulator',
  threshold_engine: 'Threshold Engine',
  experiment_planner: 'Experiment Planner',
};
