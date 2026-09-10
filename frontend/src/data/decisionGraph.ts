import type { GraphRelation } from '@/types';

/* -------------------------------------------------------------------------- *
 * Decision dependency graph - shared layout constants.
 *
 * The graph itself is now built per-decision from real analysis entities -
 * see `@/lib/buildDecisionGraph` - rather than hand-authored here. This
 * module only keeps the presentational constants both the builder and the
 * canvas need to agree on.
 * -------------------------------------------------------------------------- */

export const relationLabel: Record<GraphRelation, string> = {
  'depends-on': 'depends on',
  'resolves-to': 'resolves to',
  'evidence-for': 'evidence for',
  'has-threshold': 'has threshold',
  affects: 'affects',
  determines: 'determines',
};

/**
 * Node cards are a fixed size, which keeps the layout deterministic and
 * lets React Flow draw edges on first paint instead of waiting for a
 * measurement pass.
 */
export const GRAPH_NODE_WIDTH = 208;
export const GRAPH_NODE_HEIGHT = 104;
