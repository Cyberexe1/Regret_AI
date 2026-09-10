import type {
  ApiAssumption,
  ApiBlindspot,
  ApiDecision,
  ApiExperiment,
  ApiThreshold,
} from '@/api/types';
import { confidenceLabel, confidenceTone, importanceLabel, importanceTone, validationStatusLabel } from '@/lib/reportModel';
import type { DecisionGraph, GraphEdgeDatum, GraphNodeDatum } from '@/types/graph';

/**
 * Builds a real decision dependency graph from actual analysis entities -
 * no hand-authored nodes, no fabricated positions beyond a simple layered
 * layout (decision -> assumptions/blindspots -> thresholds -> experiments),
 * computed here rather than stored, since the real entity set differs per
 * decision and can't be authored by hand.
 *
 * Edges are derived only from real relationships the backend actually
 * recorded (`related_assumption_ids`, `related_regret_scenario_ids`,
 * `target_threshold_id`, etc.) - never invented. A threshold/experiment
 * with no recorded relationship to anything simply has no incoming edge
 * from that layer, which the graph renders correctly (an isolated node)
 * rather than force-connecting it to something arbitrary.
 */

const ROW_GAP = 180;
const COLUMN_GAP = 240;

function layoutRow(count: number, rowIndex: number): { x: number; y: number }[] {
  const totalWidth = count * COLUMN_GAP;
  const startX = -totalWidth / 2 + COLUMN_GAP / 2;
  return Array.from({ length: count }, (_, index) => ({
    x: startX + index * COLUMN_GAP,
    y: rowIndex * ROW_GAP,
  }));
}

export function buildDecisionGraph(
  decision: ApiDecision,
  assumptions: ApiAssumption[],
  blindspots: ApiBlindspot[],
  thresholds: ApiThreshold[],
  experiments: ApiExperiment[],
): DecisionGraph {
  const nodes: GraphNodeDatum[] = [];
  const edges: GraphEdgeDatum[] = [];

  const decisionNodeId = `decision-${decision.id}`;
  nodes.push({
    id: decisionNodeId,
    category: 'decision',
    title: decision.title,
    typeLabel: 'Decision under test',
    metrics: [
      { label: 'Assumptions', value: String(assumptions.length) },
      { label: 'Blindspots', value: String(blindspots.length) },
      { label: 'Thresholds', value: String(thresholds.length) },
    ],
    whyItMatters: 'Every node below this one is something the decision depends on or is measured against.',
    position: { x: 0, y: 0 },
  });

  const assumptionAndBlindspotPositions = layoutRow(assumptions.length + blindspots.length, 1);
  let positionIndex = 0;

  for (const assumption of assumptions) {
    const nodeId = `assumption-${assumption.id}`;
    nodes.push({
      id: nodeId,
      category: 'assumption',
      title: assumption.statement,
      typeLabel: 'Assumption',
      metrics: [
        { label: 'Importance', value: importanceLabel(assumption.importance), tone: importanceTone(assumption.importance) },
        { label: 'Confidence', value: confidenceLabel(assumption.confidence), tone: confidenceTone(assumption.confidence) },
        { label: 'Evidence status', value: assumption.evidence_status.replace('_', ' ') },
      ],
      whyItMatters: assumption.failure_consequence ?? assumption.reason ?? 'This is something the decision depends on without direct verification.',
      position: assumptionAndBlindspotPositions[positionIndex++]!,
    });
    edges.push({ id: `edge-${decisionNodeId}-${nodeId}`, source: decisionNodeId, target: nodeId, relation: 'depends-on' });
  }

  for (const blindspot of blindspots) {
    const nodeId = `blindspot-${blindspot.id}`;
    nodes.push({
      id: nodeId,
      category: 'uncertainty',
      title: blindspot.question,
      typeLabel: 'Blindspot',
      metrics: [
        { label: 'Importance', value: importanceLabel(blindspot.importance), tone: importanceTone(blindspot.importance) },
        { label: 'Evidence status', value: blindspot.evidence_status.replace('_', ' ') },
      ],
      whyItMatters: blindspot.why_it_matters ?? 'A category of consideration missing from the decision\u2019s framing.',
      position: assumptionAndBlindspotPositions[positionIndex++]!,
    });
    edges.push({ id: `edge-${decisionNodeId}-${nodeId}`, source: decisionNodeId, target: nodeId, relation: 'depends-on' });

    for (const relatedId of blindspot.related_assumption_ids) {
      const targetId = `assumption-${relatedId}`;
      if (nodes.some((node) => node.id === targetId)) {
        edges.push({ id: `edge-${nodeId}-${targetId}`, source: nodeId, target: targetId, relation: 'affects' });
      }
    }
  }

  const thresholdPositions = layoutRow(thresholds.length, 2);
  thresholds.forEach((threshold, index) => {
    const nodeId = `threshold-${threshold.id}`;
    nodes.push({
      id: nodeId,
      category: 'threshold',
      title: threshold.variable,
      caption: threshold.threshold_value ? `${threshold.threshold_value}${threshold.unit ?? ''}` : validationStatusLabel(threshold.validation_status),
      typeLabel: 'Threshold',
      metrics: [
        { label: 'Validation', value: validationStatusLabel(threshold.validation_status) },
        ...(threshold.threshold_value ? [{ label: 'Value', value: `${threshold.threshold_value}${threshold.unit ?? ''}` }] : []),
      ],
      whyItMatters: threshold.consequence ?? 'The tipping point at which this decision\u2019s outcome changes.',
      actionable: true,
      position: thresholdPositions[index]!,
    });

    for (const relatedId of threshold.related_assumption_ids) {
      const sourceId = `assumption-${relatedId}`;
      if (nodes.some((node) => node.id === sourceId)) {
        edges.push({ id: `edge-${sourceId}-${nodeId}`, source: sourceId, target: nodeId, relation: 'has-threshold' });
      }
    }
  });

  const experimentPositions = layoutRow(experiments.length, 3);
  experiments.forEach((experiment, index) => {
    const nodeId = `experiment-${experiment.id}`;
    nodes.push({
      id: nodeId,
      category: 'outcome',
      title: experiment.title,
      typeLabel: 'Experiment',
      metrics: [
        { label: 'Status', value: experiment.status },
        ...(experiment.duration_days !== null ? [{ label: 'Duration', value: `${experiment.duration_days} days` }] : []),
      ],
      whyItMatters: experiment.decision_rule ?? experiment.hypothesis,
      position: experimentPositions[index]!,
    });

    if (experiment.target_threshold_id) {
      const sourceId = `threshold-${experiment.target_threshold_id}`;
      if (nodes.some((node) => node.id === sourceId)) {
        edges.push({ id: `edge-${sourceId}-${nodeId}`, source: sourceId, target: nodeId, relation: 'resolves-to' });
      }
    }
  });

  return {
    decisionId: decision.id,
    decisionTitle: decision.title,
    nodes,
    edges,
    defaultNodeId: decisionNodeId,
  };
}
