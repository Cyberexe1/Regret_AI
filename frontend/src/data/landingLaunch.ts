import {
  Braces,
  CircleDot,
  FileText,
  FlaskConical,
  Gauge,
  GitBranch,
  Layers,
  Network,
  ScanSearch,
  Scale,
  ShieldAlert,
  Sparkles,
  SquarePen,
  Wind,
  type LucideIcon,
} from 'lucide-react';
import { ROUTES } from './navigation';

/* -------------------------------------------------------------------------- *
 * Landing page content â€” "Launch" layout.
 *
 * The page adapts the Launch UI dark-mode desktop composition (navbar, hero +
 * mockup, logo strip, 2x2 bento, item grid, rising feature, tabs, FAQ, CTA,
 * footer). Only the copy is ours: every band below describes REGRET ENGINE,
 * not the template. The reference's testimonial and pricing bands are
 * deliberately omitted — there are no customers to quote and nothing to sell
 * while the engine is a prototype.
 *
 * Copy lives here so section components stay layout-only.
 * -------------------------------------------------------------------------- */

export const LAUNCH_ANCHORS = {
  product: 'product',
  howItWorks: 'how-it-works',
  capabilities: 'capabilities',
  workflow: 'workflow',
  faq: 'faq',
} as const;

export interface LaunchNavLink {
  label: string;
  href: string;
}

export const launchNavLinks: LaunchNavLink[] = [
  { label: 'Product', href: `#${LAUNCH_ANCHORS.product}` },
  { label: 'How it works', href: `#${LAUNCH_ANCHORS.howItWorks}` },
  { label: 'Capabilities', href: `#${LAUNCH_ANCHORS.capabilities}` },
  { label: 'FAQ', href: `#${LAUNCH_ANCHORS.faq}` },
];

/* --- Hero ---------------------------------------------------------------- */

export const hero = {
  badge: 'Six adversarial agents. One verdict.',
  badgeLink: { label: 'See the workflow', href: `#${LAUNCH_ANCHORS.howItWorks}` },
  title: 'Know what could make your decision fail',
  lead: 'REGRET ENGINE stress-tests consequential decisions: it surfaces the assumptions you never stated, names the conditions that break them, and hands you the cheapest experiment worth running before you commit.',
  primary: { label: 'Analyze a decision', to: ROUTES.newDecision },
  secondary: { label: 'How it works', href: `#${LAUNCH_ANCHORS.howItWorks}` },
} as const;

/* --- Logo strip ---------------------------------------------------------- */

export interface StackItem {
  icon: LucideIcon;
  name: string;
  version?: string;
}

export const stackHeading = 'Built with the tools you already trust';

export const stack: StackItem[] = [
  { icon: Braces, name: 'FastAPI', version: '0.115' },
  { icon: CircleDot, name: 'React', version: '19.2' },
  { icon: Layers, name: 'TypeScript', version: '5.9' },
  { icon: Wind, name: 'Tailwind CSS', version: '4.3' },
  { icon: Sparkles, name: 'Framer Motion', version: '13.2' },
];

/* --- Bento grid ---------------------------------------------------------- */

export type BentoIllustration = 'globe' | 'ripple' | 'tiles' | 'chat';

export interface BentoTile {
  title: string;
  body: string;
  illustration: BentoIllustration;
}

/**
 * Order matters: tiles 1-2 form the top row (narrow, wide) and tiles 3-4 the
 * bottom row (wide, narrow), mirroring the reference composition.
 */
export const bentoHeading = 'Make a better decision, sooner.';

export const bentoTiles: BentoTile[] = [
  {
    title: 'Every assumption, mapped',
    body: 'Your reasoning is split into what you actually stated and what you quietly assumed, then each assumption is scored by how easily it breaks.',
    illustration: 'globe',
  },
  {
    title: 'One question at the centre',
    body: 'Analysis converges on the single uncertainty that decides the outcome, instead of handing back twenty things to worry about at once.',
    illustration: 'ripple',
  },
  {
    title: 'Six agents over one decision',
    body: 'Assumption hunter, blindspot hunter, devilâ€™s advocate, regret simulator, threshold engine and experiment planner each read the same decision and disagree in the open. Their conflicts are the useful part.',
    illustration: 'tiles',
  },
  {
    title: 'Adversarial on purpose',
    body: 'The engine argues against you deliberately, then records where your framing held and where it gave way, so a verdict always arrives with its counter-case attached.',
    illustration: 'chat',
  },
];

/* --- Capability items ---------------------------------------------------- */

export interface CapabilityItem {
  icon: LucideIcon;
  title: string;
  body: string;
}

export const capabilitiesHeading = 'Everything you need. Nothing you donâ€™t.';

export const capabilityItems: CapabilityItem[] = [
  {
    icon: Layers,
    title: 'Hidden assumptions',
    body: 'Separates stated facts from silent assumptions and scores each by how easily it breaks.',
  },
  {
    icon: ScanSearch,
    title: 'Blindspot discovery',
    body: 'Names the categories missing from your framing, each with the question that forces it open.',
  },
  {
    icon: ShieldAlert,
    title: 'Adversarial stress test',
    body: 'Attacks the framing itself rather than collecting reasons the decision might work.',
  },
  {
    icon: GitBranch,
    title: 'Regret simulation',
    body: 'Projects how the choice reads back at six months, one year, three years and five years.',
  },
  {
    icon: Gauge,
    title: 'Failure thresholds',
    body: 'Names the value at which the decision stops making sense, and the signal that arrives first.',
  },
  {
    icon: FlaskConical,
    title: 'Experiment planning',
    body: 'Ranks the cheapest tests by how much uncertainty each one actually removes.',
  },
  {
    icon: Scale,
    title: 'Value of information',
    body: 'Prices each unanswered question, so you spend on evidence that can still change the answer.',
  },
  {
    icon: Network,
    title: 'Dependency graph',
    body: 'Shows how assumptions, evidence and thresholds hang off each other in one view.',
  },
];

/* --- Rising feature ------------------------------------------------------ */

export const rising = {
  title: 'Confidence you can defend. And revisit.',
  lead: 'Every verdict carries the assumptions, thresholds and evidence it was built from. Re-open the decision in six months and you can see exactly what you believed, what you tested, and which belief turned out to be wrong.',
} as const;

/* --- Workflow tabs ------------------------------------------------------- */

export type MockupVariant = 'intake' | 'analysis' | 'report';

export interface WorkflowTab {
  icon: LucideIcon;
  title: string;
  body: string;
  mockup: MockupVariant;
}

export const workflowHeading = 'From a vague worry to a testable claim';
export const workflowLead =
  'Three screens carry a decision from the moment it is bothering you to the experiment that settles it.';

export const workflowTabs: WorkflowTab[] = [
  {
    icon: SquarePen,
    title: 'State the decision',
    body: 'Write it in your own words, with the constraints that actually bind and the date you have to commit by.',
    mockup: 'intake',
  },
  {
    icon: ScanSearch,
    title: 'Watch the engine work',
    body: 'Assumptions surfaced, blindspots named, thresholds calculated, each agent reporting as it finishes.',
    mockup: 'analysis',
  },
  {
    icon: FileText,
    title: 'Read one page',
    body: 'Critical uncertainty, the breaking point, the recommended experiment and what it costs. Nothing else competing for attention.',
    mockup: 'report',
  },
];

/* --- FAQ ----------------------------------------------------------------- */

export interface FaqItem {
  question: string;
  answer: string;
}

export const faqHeading = 'Questions and answers';

export const faqItems: FaqItem[] = [
  {
    question: 'Does it tell me what to decide?',
    answer:
      'No. It returns the assumptions your decision depends on, the point at which each one breaks, and the cheapest test that would settle the most important of them. The output is an experiment, not an answer.',
  },
  {
    question: 'What makes this different from asking a chatbot?',
    answer:
      'A single model tends to agree with the framing it was handed. Here, six agents work the same decision with opposing objectives, and one of them exists purely to argue against you. Disagreement between them is recorded rather than smoothed over.',
  },
  {
    question: 'How long does an analysis take?',
    answer:
      'A few minutes for a well-stated decision. Each agent reports as it finishes, so assumptions and blindspots appear before thresholds and regret projections are done.',
  },
  {
    question: 'What kind of decisions is it for?',
    answer:
      'Ones that are expensive to reverse: capital commitments, migrations, hires, pricing changes, career moves. If the choice is cheap to undo, the engine will usually tell you to just try it.',
  },
  {
    question: 'Is my decision data private?',
    answer:
      'Decisions stay in your workspace and are never used to train models. This build stores them locally against the development backend.',
  },
  {
    question: 'Can I re-open a decision later?',
    answer:
      'Yes, that is the point of the archive. Every report keeps the assumptions, thresholds and evidence it was built from, so you can check months later which belief turned out to be wrong.',
  },
];

/* --- CTA ----------------------------------------------------------------- */

export const cta = {
  title: 'Stop guessing. Start stress-testing.',
  primary: { label: 'Analyze a decision', to: ROUTES.newDecision },
  secondary: { label: 'Open workspace', to: ROUTES.dashboard },
} as const;

/* --- Footer -------------------------------------------------------------- */

export interface FooterColumn {
  heading: string;
  links: { label: string; to: string; external?: boolean }[];
}

export const footerColumns: FooterColumn[] = [
  {
    heading: 'Product',
    links: [
      { label: 'How it works', to: `#${LAUNCH_ANCHORS.howItWorks}`, external: true },
      { label: 'Capabilities', to: `#${LAUNCH_ANCHORS.capabilities}`, external: true },
      { label: 'Questions', to: `#${LAUNCH_ANCHORS.faq}`, external: true },
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
  {
    heading: 'Engine',
    links: [
      { label: 'Assumption hunter', to: `#${LAUNCH_ANCHORS.capabilities}`, external: true },
      { label: 'Threshold engine', to: `#${LAUNCH_ANCHORS.capabilities}`, external: true },
      { label: 'Experiment planner', to: `#${LAUNCH_ANCHORS.capabilities}`, external: true },
      { label: 'Decision graph', to: `#${LAUNCH_ANCHORS.capabilities}`, external: true },
    ],
  },
];

export const footerLegal = [
  { label: 'Privacy policy', href: `#${LAUNCH_ANCHORS.faq}` },
  { label: 'Terms of service', href: `#${LAUNCH_ANCHORS.faq}` },
];
