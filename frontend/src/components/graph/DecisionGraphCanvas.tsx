import { useCallback, useMemo, useState, type CSSProperties } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type NodeHandle,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  GRAPH_NODE_HEIGHT,
  GRAPH_NODE_WIDTH,
  relationLabel,
} from '@/data/decisionGraph';
import type { DecisionGraph, GraphRelation } from '@/types';
import { GraphNodeCard, type GraphCardNode } from './GraphNodeCard';

/** Must be module-scoped: a new object each render makes React Flow warn. */
const nodeTypes = { card: GraphNodeCard };

/**
 * Handle geometry declared up front.
 *
 * React Flow normally derives this by measuring the DOM, and refuses to draw an
 * edge until both endpoints are measured. Because every card is exactly
 * GRAPH_NODE_WIDTH x GRAPH_NODE_HEIGHT, the positions are known in advance, so
 * declaring them lets edges render correctly on first paint with no measurement
 * round-trip and no layout flash.
 */
const NODE_HANDLES: NodeHandle[] = (() => {
  const midX = GRAPH_NODE_WIDTH / 2;
  const midY = GRAPH_NODE_HEIGHT / 2;

  return [
    { id: 't-top', type: 'target', position: Position.Top, x: midX, y: 0, width: 1, height: 1 },
    { id: 't-left', type: 'target', position: Position.Left, x: 0, y: midY, width: 1, height: 1 },
    {
      id: 's-bottom',
      type: 'source',
      position: Position.Bottom,
      x: midX,
      y: GRAPH_NODE_HEIGHT,
      width: 1,
      height: 1,
    },
    {
      id: 's-right',
      type: 'source',
      position: Position.Right,
      x: GRAPH_NODE_WIDTH,
      y: midY,
      width: 1,
      height: 1,
    },
  ];
})();

const RELATION_COLOR: Record<GraphRelation, string> = {
  'depends-on': 'var(--color-accent)',
  'resolves-to': 'var(--color-accent)',
  'evidence-for': 'var(--color-ink-faint)',
  'has-threshold': 'var(--color-danger)',
  affects: 'var(--color-ink-muted)',
  determines: 'var(--color-success)',
};

/** Themes React Flow's own chrome through its CSS variables. */
const FLOW_THEME = {
  '--xy-background-color': 'transparent',
  '--xy-controls-button-background-color': 'var(--color-surface-raised)',
  '--xy-controls-button-background-color-hover': 'var(--color-surface-overlay)',
  '--xy-controls-button-color': 'var(--color-ink-secondary)',
  '--xy-controls-button-color-hover': 'var(--color-ink)',
  '--xy-controls-button-border-color': 'var(--color-hairline)',
  '--xy-attribution-background-color': 'transparent',
} as CSSProperties;

export interface DecisionGraphCanvasProps {
  graph: DecisionGraph;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export function DecisionGraphCanvas({ graph, selectedId, onSelect }: DecisionGraphCanvasProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Hover previews a node without changing the selection.
  const focusId = hoveredId ?? selectedId;

  const relatedIds = useMemo(() => {
    if (!focusId) return null;

    const ids = new Set<string>([focusId]);
    for (const edge of graph.edges) {
      if (edge.source === focusId) ids.add(edge.target);
      if (edge.target === focusId) ids.add(edge.source);
    }
    return ids;
  }, [focusId, graph.edges]);

  const nodes = useMemo<GraphCardNode[]>(
    () =>
      graph.nodes.map((node) => ({
        id: node.id,
        type: 'card',
        position: node.position,
        // Declared so edges render immediately rather than after measurement.
        width: GRAPH_NODE_WIDTH,
        height: GRAPH_NODE_HEIGHT,
        handles: NODE_HANDLES,
        data: {
          category: node.category,
          title: node.title,
          caption: node.caption,
          active: node.id === selectedId,
          dimmed: relatedIds ? !relatedIds.has(node.id) : false,
        },
      })),
    [graph.nodes, selectedId, relatedIds],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => {
        const horizontal = edge.anchor === 'horizontal';
        const inFocus = focusId ? edge.source === focusId || edge.target === focusId : true;
        const color = RELATION_COLOR[edge.relation];

        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: horizontal ? 's-right' : 's-bottom',
          targetHandle: horizontal ? 't-left' : 't-top',
          type: 'smoothstep',
          // Relation labels appear only for the focused node, to avoid clutter.
          label: focusId && inFocus ? relationLabel[edge.relation] : undefined,
          labelStyle: { fill: 'var(--color-ink-secondary)', fontSize: 10, fontWeight: 500 },
          labelBgStyle: { fill: 'var(--color-surface-overlay)' },
          labelBgPadding: [6, 3] as [number, number],
          labelBgBorderRadius: 4,
          style: {
            stroke: color,
            strokeWidth: inFocus ? 1.8 : 1.2,
            strokeDasharray: edge.relation === 'evidence-for' ? '4 4' : undefined,
            opacity: inFocus ? 1 : 0.22,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 14,
            height: 14,
            color,
          },
        };
      }),
    [graph.edges, focusId],
  );

  const onNodeClick = useCallback(
    (_event: unknown, node: { id: string }) => {
      onSelect(node.id === selectedId ? null : node.id);
    },
    [onSelect, selectedId],
  );

  return (
    <div className="size-full" style={FLOW_THEME}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        colorMode="dark"
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.3}
        maxZoom={1.6}
        /* Read-only: no dragging, connecting, or built-in selection. */
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        edgesFocusable={false}
        /* Wheel pans the page, not the canvas; zoom is via controls or pinch. */
        zoomOnScroll={false}
        preventScrolling={false}
        onNodeClick={onNodeClick}
        onNodeMouseEnter={(_event, node) => setHoveredId(node.id)}
        onNodeMouseLeave={() => setHoveredId(null)}
        onPaneClick={() => onSelect(null)}
        aria-label="Decision dependency graph"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          size={1}
          color="var(--color-hairline-strong)"
        />
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
    </div>
  );
}
