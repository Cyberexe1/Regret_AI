import type { Tone } from './index';

/* -------------------------------------------------------------------------- *
 * Decision dependency graph
 *
 * A layered, directional model of what a decision rests on. Positions are
 * authored by hand rather than produced by a force layout, so the structure
 * always reads top-down instead of as a cloud of circles.
 * -------------------------------------------------------------------------- */

export const GRAPH_CATEGORIES = [
  'decision',
  'assumption',
  'evidence',
  'uncertainty',
  'threshold',
  'outcome',
] as const;

export type GraphCategory = (typeof GRAPH_CATEGORIES)[number];

export interface GraphMetric {
  label: string;
  value: string;
  tone?: Tone;
}

export interface GraphNodeDatum {
  id: string;
  category: GraphCategory;
  title: string;
  /** Short value rendered on the node itself. */
  caption?: string;
  /** Human-readable type shown in the detail panel. */
  typeLabel: string;
  metrics: GraphMetric[];
  whyItMatters: string;
  /** Offers the experiment CTA in the detail panel. */
  actionable?: boolean;
  position: { x: number; y: number };
}

export type GraphRelation =
  | 'depends-on'
  | 'resolves-to'
  | 'evidence-for'
  | 'has-threshold'
  | 'affects'
  | 'determines';

/** Which side of each node the edge attaches to. */
export type GraphAnchor = 'vertical' | 'horizontal';

export interface GraphEdgeDatum {
  id: string;
  source: string;
  target: string;
  relation: GraphRelation;
  /** `horizontal` routes from the source's right into the target's left. */
  anchor?: GraphAnchor;
}

export interface DecisionGraph {
  decisionId: string;
  decisionTitle: string;
  nodes: GraphNodeDatum[];
  edges: GraphEdgeDatum[];
  /** Node selected when the page opens. */
  defaultNodeId: string;
}
