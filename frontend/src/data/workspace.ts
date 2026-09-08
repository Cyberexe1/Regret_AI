export type WorkspacePlan = 'Free' | 'Analyst' | 'Operator' | 'Enterprise';

export interface WorkspaceSubscription {
  plan: WorkspacePlan;
  /** Analyses left in the current billing month. */
  analysesRemaining: number;
  analysesPerMonth: number;
  renewsOn: string;
}

export interface WorkspaceProfile {
  workspaceName: string;
  plan: WorkspacePlan;
  user: {
    name: string;
    role: string;
    email: string;
  };
}

/** Local placeholder identity. Replaced once accounts exist. */
export const workspaceProfile: WorkspaceProfile = {
  workspaceName: 'Northline Studio',
  plan: 'Free',
  user: {
    name: 'Alex Morgan',
    role: 'Founder',
    email: 'alex@example.com',
  },
};

/** Mock plan state. No billing is wired up. */
export const workspaceSubscription: WorkspaceSubscription = {
  plan: workspaceProfile.plan,
  analysesRemaining: 3,
  analysesPerMonth: 5,
  renewsOn: '2026-10-01T00:00:00.000Z',
};
