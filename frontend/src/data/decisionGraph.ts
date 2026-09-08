import type { DecisionGraph, GraphRelation } from '@/types';

/* -------------------------------------------------------------------------- *
 * Dependency graph for the cloud kitchen decision.
 *
 * Six layers, top to bottom:
 *   decision -> assumptions -> uncertainties -> thresholds -> outcomes
 * with evidence feeding in horizontally beside the uncertainty it supports.
 *
 * Figures match data/decisionReport.ts so the two views never disagree.
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
 * Node cards are a fixed size, which keeps the authored layout deterministic
 * and lets React Flow draw edges on first paint instead of waiting for a
 * measurement pass.
 */
export const GRAPH_NODE_WIDTH = 208;
export const GRAPH_NODE_HEIGHT = 104;

const cloudKitchenGraph: DecisionGraph = {
  decisionId: 'dcn-5104',
  decisionTitle: 'Start a cloud kitchen',
  defaultNodeId: 'gn-repeat',

  nodes: [
    /* --- Layer 0: the decision ------------------------------------------- */
    {
      id: 'gn-decision',
      category: 'decision',
      title: 'Start a cloud kitchen',
      caption: '₹5,00,000 · 6 months',
      typeLabel: 'Decision under test',
      metrics: [
        { label: 'Commitment', value: '₹5,00,000' },
        { label: 'Reversibility', value: 'Costly to reverse', tone: 'warning' },
        { label: 'Depends on', value: '4 assumptions' },
        { label: 'Risk level', value: 'Medium', tone: 'warning' },
      ],
      whyItMatters:
        'Everything below this node is what the decision quietly rests on. If any branch fails, the commitment fails with it.',
      position: { x: 430, y: 0 },
    },

    /* --- Layer 1: assumptions -------------------------------------------- */
    {
      id: 'gn-demand',
      category: 'assumption',
      title: 'Customer demand',
      caption: '42 orders/day needed',
      typeLabel: 'Assumption',
      metrics: [
        { label: 'Required volume', value: '42 orders/day' },
        { label: 'Support', value: 'Uncertain', tone: 'warning' },
        { label: 'Resolves to', value: 'Repeat customer rate' },
      ],
      whyItMatters:
        'Volume alone does not carry the model. Demand only becomes profitable once a share of it returns without being paid for twice.',
      position: { x: 60, y: 170 },
    },
    {
      id: 'gn-aov',
      category: 'assumption',
      title: 'Average order value',
      caption: '₹340',
      typeLabel: 'Assumption',
      metrics: [
        { label: 'Assumed', value: '₹340' },
        { label: 'Support', value: 'Supported', tone: 'success' },
        { label: 'Sensitivity', value: 'Moderate' },
      ],
      whyItMatters:
        'Order value is backed by menu pricing and comparable listings. It feeds contribution directly, but it is not where the risk sits.',
      position: { x: 290, y: 170 },
    },
    {
      id: 'gn-commission',
      category: 'assumption',
      title: 'Platform commission',
      caption: '22% modelled · 25–30% observed',
      typeLabel: 'Assumption',
      metrics: [
        { label: 'Modelled at', value: '22%' },
        { label: 'Observed range', value: '25–30%', tone: 'warning' },
        { label: 'Support', value: 'Uncertain', tone: 'warning' },
        { label: 'Effect on break-even', value: '+1 point of repeat rate' },
      ],
      whyItMatters:
        'The base rate is contractual, but the effective rate after mandatory promotions is three to eight points higher. That gap moves break-even against you.',
      position: { x: 520, y: 170 },
    },
    {
      id: 'gn-cac',
      category: 'assumption',
      title: 'Customer acquisition cost',
      caption: '₹180–₹240',
      typeLabel: 'Assumption',
      metrics: [
        { label: 'Current estimate', value: '₹180–₹240', tone: 'warning' },
        { label: 'Support', value: 'Uncertain', tone: 'warning' },
        { label: 'Resolves to', value: 'Blended acquisition cost' },
      ],
      whyItMatters:
        'Paid placement is the only reliable discovery channel at launch, so acquisition cost sets the floor on how cheap a customer can be.',
      position: { x: 750, y: 170 },
    },

    /* --- Evidence, feeding in horizontally -------------------------------- */
    {
      id: 'gn-ev-benchmarks',
      category: 'evidence',
      title: 'Category benchmarks',
      caption: '2 aggregator reports',
      typeLabel: 'Evidence',
      metrics: [
        { label: 'Strength', value: 'Indirect' },
        { label: 'Reports', value: '18–21% city average' },
      ],
      whyItMatters:
        'Published benchmarks describe the category, not this menu at this price point. Useful as a prior, not as proof.',
      position: { x: -210, y: 250 },
    },
    {
      id: 'gn-ev-discount',
      category: 'evidence',
      title: 'Discount-led launch data',
      caption: 'Overstates retention',
      typeLabel: 'Evidence',
      metrics: [
        { label: 'Strength', value: 'Cautionary' },
        { label: 'Effect', value: 'Inflates early repeat rate' },
      ],
      whyItMatters:
        'Launch weeks run on discounts, which reliably overstate repeat behaviour. Any measurement has to outlast the promotion.',
      position: { x: -210, y: 370 },
    },
    {
      id: 'gn-ev-gap',
      category: 'evidence',
      title: 'No first-party data',
      caption: 'Evidence gap',
      typeLabel: 'Evidence gap',
      metrics: [
        { label: 'Strength', value: 'None', tone: 'danger' },
        { label: 'Missing', value: 'Repeat orders at full price' },
      ],
      whyItMatters:
        'Nobody has paid for this food twice without a discount attached. This is the single largest hole in the case.',
      position: { x: -210, y: 490 },
    },
    {
      id: 'gn-ev-comparables',
      category: 'evidence',
      title: 'Comparable launches',
      caption: '₹195 and ₹240',
      typeLabel: 'Evidence',
      metrics: [
        { label: 'Strength', value: 'Partial' },
        { label: 'Observed', value: '₹195 and ₹240' },
      ],
      whyItMatters:
        'Two comparable launches straddle the sustainable ceiling, so the evidence neither confirms nor rules out the assumption.',
      position: { x: 1010, y: 350 },
    },

    /* --- Layer 2: uncertainties ------------------------------------------ */
    {
      id: 'gn-repeat',
      category: 'uncertainty',
      title: 'Repeat customer rate',
      caption: '18–21% · needs 24%',
      typeLabel: 'Critical uncertainty',
      metrics: [
        { label: 'Current estimate', value: '18–21%', tone: 'warning' },
        { label: 'Threshold', value: '24%', tone: 'danger' },
        { label: 'Confidence', value: 'Low', tone: 'danger' },
        { label: 'Impact', value: 'High', tone: 'danger' },
        { label: 'Evidence', value: '3 sources' },
      ],
      whyItMatters:
        'Below this threshold, the decision becomes materially harder to sustain.',
      actionable: true,
      position: { x: 60, y: 350 },
    },
    {
      id: 'gn-cac-blended',
      category: 'uncertainty',
      title: 'Blended acquisition cost',
      caption: 'Ceiling ₹210',
      typeLabel: 'Uncertainty',
      metrics: [
        { label: 'Current estimate', value: '₹180–₹240', tone: 'warning' },
        { label: 'Maximum sustainable', value: '₹210', tone: 'danger' },
        { label: 'Confidence', value: 'Low', tone: 'danger' },
        { label: 'Impact', value: 'High', tone: 'danger' },
        { label: 'Evidence', value: '1 source' },
      ],
      whyItMatters:
        'The upper end of the estimate already exceeds what the unit economics can carry, which compounds the repeat-rate problem rather than offsetting it.',
      actionable: true,
      position: { x: 750, y: 350 },
    },

    /* --- Layer 3: thresholds --------------------------------------------- */
    {
      id: 'gn-retention-threshold',
      category: 'threshold',
      title: 'Retention threshold',
      caption: '24% repeat rate',
      typeLabel: 'Failure threshold',
      metrics: [
        { label: 'Breaks below', value: '24%', tone: 'danger' },
        { label: 'Break-even at', value: '22%' },
        { label: 'Current position', value: 'Below break-even', tone: 'danger' },
      ],
      whyItMatters:
        'This is the breaking point of the whole decision. Above it the model compounds; below it every new customer deepens the loss.',
      actionable: true,
      position: { x: 60, y: 530 },
    },
    {
      id: 'gn-cac-ceiling',
      category: 'threshold',
      title: 'Acquisition ceiling',
      caption: '₹210 per customer',
      typeLabel: 'Failure threshold',
      metrics: [
        { label: 'Breaks above', value: '₹210', tone: 'danger' },
        { label: 'Current estimate', value: 'Straddles the ceiling', tone: 'warning' },
      ],
      whyItMatters:
        'Past this ceiling the payback period outlives the customer, and a higher repeat rate is needed just to stand still.',
      position: { x: 750, y: 530 },
    },

    /* --- Layer 4: outcomes ----------------------------------------------- */
    {
      id: 'gn-contribution',
      category: 'outcome',
      title: 'Monthly contribution',
      caption: '-₹30k at current estimate',
      typeLabel: 'Modelled outcome',
      metrics: [
        { label: 'At 18–21% repeat', value: '-₹30,000', tone: 'danger' },
        { label: 'At 24% repeat', value: '+₹16,000', tone: 'success' },
        { label: 'Driven by', value: '4 inputs' },
      ],
      whyItMatters:
        'Contribution is where every branch of the graph converges. It is negative at the current estimate and positive only past the threshold.',
      position: { x: 405, y: 710 },
    },
    {
      id: 'gn-profitability',
      category: 'outcome',
      title: 'Profitability',
      caption: 'Not reached at current estimate',
      typeLabel: 'Terminal outcome',
      metrics: [
        { label: 'Status', value: 'Not reached', tone: 'danger' },
        { label: 'Requires', value: 'Repeat rate at or above 24%' },
        { label: 'Earliest signal', value: 'Second-order rate, day 14' },
      ],
      whyItMatters:
        'The decision succeeds or fails here. Everything upstream is a lever on this single result.',
      position: { x: 405, y: 880 },
    },
  ],

  edges: [
    { id: 'ge-1', source: 'gn-decision', target: 'gn-demand', relation: 'depends-on' },
    { id: 'ge-2', source: 'gn-decision', target: 'gn-aov', relation: 'depends-on' },
    { id: 'ge-3', source: 'gn-decision', target: 'gn-commission', relation: 'depends-on' },
    { id: 'ge-4', source: 'gn-decision', target: 'gn-cac', relation: 'depends-on' },

    { id: 'ge-5', source: 'gn-demand', target: 'gn-repeat', relation: 'resolves-to' },
    { id: 'ge-6', source: 'gn-cac', target: 'gn-cac-blended', relation: 'resolves-to' },

    {
      id: 'ge-7',
      source: 'gn-ev-benchmarks',
      target: 'gn-repeat',
      relation: 'evidence-for',
      anchor: 'horizontal',
    },
    {
      id: 'ge-8',
      source: 'gn-ev-discount',
      target: 'gn-repeat',
      relation: 'evidence-for',
      anchor: 'horizontal',
    },
    {
      id: 'ge-9',
      source: 'gn-ev-gap',
      target: 'gn-repeat',
      relation: 'evidence-for',
      anchor: 'horizontal',
    },
    {
      id: 'ge-10',
      source: 'gn-ev-comparables',
      target: 'gn-cac-blended',
      relation: 'evidence-for',
      anchor: 'horizontal',
    },

    {
      id: 'ge-11',
      source: 'gn-repeat',
      target: 'gn-retention-threshold',
      relation: 'has-threshold',
    },
    {
      id: 'ge-12',
      source: 'gn-cac-blended',
      target: 'gn-cac-ceiling',
      relation: 'has-threshold',
    },

    {
      id: 'ge-13',
      source: 'gn-retention-threshold',
      target: 'gn-contribution',
      relation: 'affects',
    },
    { id: 'ge-14', source: 'gn-cac-ceiling', target: 'gn-contribution', relation: 'affects' },
    { id: 'ge-15', source: 'gn-aov', target: 'gn-contribution', relation: 'affects' },
    { id: 'ge-16', source: 'gn-commission', target: 'gn-contribution', relation: 'affects' },

    {
      id: 'ge-17',
      source: 'gn-contribution',
      target: 'gn-profitability',
      relation: 'determines',
    },
  ],
};

const graphsByDecisionId: Record<string, DecisionGraph> = {
  [cloudKitchenGraph.decisionId]: cloudKitchenGraph,
};

export function findDecisionGraph(decisionId: string): DecisionGraph | undefined {
  return graphsByDecisionId[decisionId];
}
