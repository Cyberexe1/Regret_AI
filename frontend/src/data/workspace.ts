export interface WorkspaceProfile {
  workspaceName: string;
  plan: 'Analyst' | 'Operator' | 'Enterprise';
  user: {
    name: string;
    role: string;
    email: string;
  };
}

/** Local placeholder identity. Replaced once accounts exist. */
export const workspaceProfile: WorkspaceProfile = {
  workspaceName: 'Northline Studio',
  plan: 'Operator',
  user: {
    name: 'Priya Raman',
    role: 'Founder',
    email: 'priya@northline.studio',
  },
};
