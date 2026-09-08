export type WorkspacePlan = 'Free' | 'Analyst' | 'Operator' | 'Enterprise';

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
    name: 'Priya Raman',
    role: 'Founder',
    email: 'priya@northline.studio',
  },
};
