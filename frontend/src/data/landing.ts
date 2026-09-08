import {
  EyeOff,
  FlaskConical,
  Gauge,
  GitBranch,
  Layers,
  ScanSearch,
  Search,
  ShieldAlert,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { ROUTES } from './navigation';
import type { Tone } from '@/types';

/* -------------------------------------------------------------------------- *
 * Landing page content.
 *
 * Copy lives here rather than inside components so sections stay small and the
 * wording can be revised without touching layout.
 * -------------------------------------------------------------------------- */

/** In-page anchor targets. Kept together so nav and sections cannot drift. */
export const LANDING_ANCHORS = {
  problem: 'problem',
  howItWorks: 'how-it-works',
  product: 'product',
  experiments: 'experiments',
  capabilities: 'capabilities',
  about: 'about',
} as const;

export interface LandingNavLink {
  label: string;
  href: string;
}

export const landingNavLinks: LandingNavLink[] = [
  { label: 'Product', href: `#${LANDING_ANCHORS.product}` },
  { label: 'How it works', href: `#${LANDING_ANCHORS.howItWorks}` },
  { label: 'Experiments', href: `#${LANDING_ANCHORS.experiments}` },
  { label: 'About', href: `#${LANDING_ANCHORS.about}` },
];

/* --- Hero interface preview ---------------------------------------------- */

export interface PreviewStage {
  label: string;
  detail: string;
  /** Right-aligned chip: a count or a state. */
  chip: string;
  tone: Tone;
}

/**
 * The five stages of an analysis, in order. Deliberately mirrors the worked
 * example further down the page so the two read as one product.
 */
export const previewStages: PreviewStage[] = [
  { label: 'Decision', detail: 'Cloud kitchen · ₹5,00,000', chip: 'Captured', tone: 'neutral' },
  { label: 'Hidden assumptions', detail: '4 surfaced · 2 never stated', chip: '4', tone: 'info' },
  { label: 'Failure conditions', detail: 'Repeat rate holds below 24%', chip: '3', tone: 'warning' },
  { label: 'Regret scenarios', detail: 'Projected 6 months → 5 years', chip: '4', tone: 'danger' },
  {
    label: 'Validation experiment',
    detail: '14-day pilot before commitment',
    chip: 'Recommended',
    tone: 'accent',
  },
];

/* --- Problem ------------------------------------------------------------- */

export interface ProblemItem {
  icon: LucideIcon;
  title: string;
  body: string;
}

export const problems: ProblemItem[] = [
  {
    icon: Search,
    title: 'We ask questions we already know to ask.',
    body: 'Familiar checklists confirm the framing you arrived with. The question that would have changed your mind is the one you never thought to ask.',
  },
  {
    icon: EyeOff,
    title: 'Important assumptions remain invisible.',
    body: 'The assumptions that break decisions are rarely written down. They sit underneath the reasoning, unexamined because they were never stated.',
  },
  {
    icon: Zap,
    title: 'We commit before testing what matters.',
    body: 'Most consequential decisions can be made later and cheaper. The test that would settle the question usually costs a fraction of the commitment.',
  },
];

/* --- Process ------------------------------------------------------------- */

export interface ProcessStep {
  index: string;
  title: string;
  body: string;
}

export const processSteps: ProcessStep[] = [
  {
    index: '01',
    title: 'Define the decision',
    body: 'State it in your own words, with the constraints that actually bind and the date you have to commit by.',
  },
  {
    index: '02',
    title: 'Discover uncertainty',
    body: 'The engine separates what you asserted from what you assumed, then scores each assumption by how easily it breaks.',
  },
  {
    index: '03',
    title: 'Stress-test failure',
    body: 'Adversarial passes attack the framing itself, searching for conditions under which the decision fails rather than reasons it works.',
  },
  {
    index: '04',
    title: 'Find the breaking point',
    body: 'Every critical uncertainty gets a threshold: the value at which the decision stops making sense, and the signal that arrives first.',
  },
  {
    index: '05',
    title: 'Run the smallest experiment',
    body: 'You get the cheapest test that would genuinely change your mind, with success criteria written down before it starts.',
  },
];

/* --- Worked example ------------------------------------------------------ */

export interface ExampleAnalysis {
  reference: string;
  decision: string;
  risk: { label: string; tone: Tone };
  criticalUncertainty: string;
  currentEvidence: string;
  requiredThreshold: string;
  /** Scale used by the threshold bar, in percentage points. */
  scaleMax: number;
  evidenceRange: [number, number];
  thresholdValue: number;
  recommendedAction: string;
  experimentCost: string;
}

export const exampleAnalysis: ExampleAnalysis = {
  reference: 'dcn-5104',
  decision: 'Should I invest ₹5,00,000 to start a cloud kitchen?',
  risk: { label: 'Medium', tone: 'warning' },
  criticalUncertainty: 'Repeat customer rate',
  currentEvidence: '18–21%',
  requiredThreshold: '24%',
  scaleMax: 35,
  evidenceRange: [18, 21],
  thresholdValue: 24,
  recommendedAction: 'Run a 14-day pilot before committing ₹5,00,000.',
  experimentCost: '14 days · ₹0 committed',
};

/* --- Capabilities -------------------------------------------------------- */

export interface Capability {
  icon: LucideIcon;
  title: string;
  body: string;
}

export const capabilities: Capability[] = [
  {
    icon: Layers,
    title: 'Hidden Assumptions',
    body: 'Separates what you stated from what you took for granted, and scores each one by how easily it breaks under real conditions.',
  },
  {
    icon: ScanSearch,
    title: 'Blindspot Discovery',
    body: 'Surfaces the categories missing from your framing, each paired with the question that forces it into the open.',
  },
  {
    icon: ShieldAlert,
    title: 'Adversarial Stress Testing',
    body: 'Argues against the decision on purpose, attacking the framing rather than collecting reasons it might work.',
  },
  {
    icon: GitBranch,
    title: 'Regret Simulation',
    body: 'Projects how the decision reads back at six months, one year, three years and five years, and what recovery costs at each point.',
  },
  {
    icon: Gauge,
    title: 'Failure Thresholds',
    body: 'Names the value at which the decision stops making sense, plus the early warning signal that shows up before you reach it.',
  },
  {
    icon: FlaskConical,
    title: 'Experiment Planning',
    body: 'Ranks the cheapest tests by how much uncertainty each one removes, so you buy the most belief for the least commitment.',
  },
];

/* --- Footer -------------------------------------------------------------- */

export interface FooterGroup {
  heading: string;
  links: { label: string; to: string; external?: boolean }[];
}

export const footerGroups: FooterGroup[] = [
  {
    heading: 'Product',
    links: [
      { label: 'How it works', to: `#${LANDING_ANCHORS.howItWorks}`, external: true },
      { label: 'Example analysis', to: `#${LANDING_ANCHORS.product}`, external: true },
      { label: 'Capabilities', to: `#${LANDING_ANCHORS.capabilities}`, external: true },
    ],
  },
  {
    heading: 'Workspace',
    links: [
      { label: 'Dashboard', to: ROUTES.dashboard },
      { label: 'New decision', to: ROUTES.newDecision },
      { label: 'Decision history', to: ROUTES.decisions },
      { label: 'Experiments', to: ROUTES.experiments },
    ],
  },
];
