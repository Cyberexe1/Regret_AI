import { useCallback, useState } from 'react';
import { workspaceProfile } from '@/data/workspace';
import type { Currency, RiskTolerance } from '@/types';

export type ThemePreference = 'dark' | 'system' | 'light';

export interface WorkspaceSettings {
  name: string;
  email: string;
  defaultRiskTolerance: RiskTolerance;
  defaultCurrency: Currency;
  showUncertaintyExplanations: boolean;
  showExperimentRecommendations: boolean;
  saveDecisionHistory: boolean;
  notifyAnalysisComplete: boolean;
  notifyExperimentMilestone: boolean;
  notifyWeeklyReview: boolean;
  theme: ThemePreference;
}

const INITIAL_SETTINGS: WorkspaceSettings = {
  name: workspaceProfile.user.name,
  email: workspaceProfile.user.email,
  defaultRiskTolerance: 'balanced',
  defaultCurrency: 'INR',
  showUncertaintyExplanations: true,
  showExperimentRecommendations: true,
  saveDecisionHistory: true,
  notifyAnalysisComplete: true,
  notifyExperimentMilestone: true,
  notifyWeeklyReview: false,
  theme: 'dark',
};

export interface WorkspaceSettingsState {
  settings: WorkspaceSettings;
  set: <K extends keyof WorkspaceSettings>(key: K, value: WorkspaceSettings[K]) => void;
  toggle: (key: BooleanSettingKey) => void;
}

/** Keys that hold a switch value. */
export type BooleanSettingKey = {
  [K in keyof WorkspaceSettings]: WorkspaceSettings[K] extends boolean ? K : never;
}[keyof WorkspaceSettings];

/**
 * Settings live in component state for the prototype: there is no account to
 * persist them against yet, and the page says so.
 */
export function useWorkspaceSettings(): WorkspaceSettingsState {
  const [settings, setSettings] = useState<WorkspaceSettings>(INITIAL_SETTINGS);

  const set = useCallback<WorkspaceSettingsState['set']>((key, value) => {
    setSettings((current) => ({ ...current, [key]: value }));
  }, []);

  const toggle = useCallback((key: BooleanSettingKey) => {
    setSettings((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  return { settings, set, toggle };
}
