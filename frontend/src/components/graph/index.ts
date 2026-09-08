export { GraphLegend } from './GraphLegend';
export { NodeDetailPanel } from './NodeDetailPanel';
export type { NodeDetailPanelProps } from './NodeDetailPanel';

// DecisionGraphCanvas and GraphNodeCard are intentionally absent: the canvas
// pulls in React Flow and its stylesheet, and is imported lazily by the page.
