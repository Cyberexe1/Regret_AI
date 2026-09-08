import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { cn } from '@/lib/cn';
import { graphCategoryLabel, graphCategoryTone, toneFill } from '@/lib/tone';
import type { GraphCategory } from '@/types';

export interface GraphCardData extends Record<string, unknown> {
  category: GraphCategory;
  title: string;
  caption?: string;
  /** Faded because another node has focus. */
  dimmed: boolean;
  /** Currently open in the detail panel. */
  active: boolean;
}

export type GraphCardNode = Node<GraphCardData, 'card'>;

/**
 * Handles exist only so edges have anchor points; this graph is read-only, so
 * they are sized to a pixel and made invisible.
 */
const HANDLE_STYLE = {
  width: 1,
  height: 1,
  minWidth: 1,
  minHeight: 1,
  border: 'none',
  background: 'transparent',
} as const;

const SHELL: Record<GraphCategory, string> = {
  decision: 'border-accent-line bg-accent-soft/45',
  assumption: 'border-info-line/60 bg-info-soft/20',
  evidence: 'border-hairline bg-surface-raised',
  uncertainty: 'border-warning-line/60 bg-warning-soft/20',
  threshold: 'border-danger-line/60 bg-danger-soft/20',
  outcome: 'border-success-line/60 bg-success-soft/20',
};

export function GraphNodeCard({ data }: NodeProps<GraphCardNode>) {
  const { category, title, caption, dimmed, active } = data;
  const isDecision = category === 'decision';

  return (
    <>
      <Handle type="target" position={Position.Top} id="t-top" style={HANDLE_STYLE} />
      <Handle type="target" position={Position.Left} id="t-left" style={HANDLE_STYLE} />

      {/* Fixed size: matches GRAPH_NODE_WIDTH / GRAPH_NODE_HEIGHT. */}
      <div
        className={cn(
          'flex h-26 w-52 flex-col overflow-hidden rounded-lg border px-3.5 py-3 transition-[opacity,box-shadow,border-color] duration-200',
          SHELL[category],
          active && 'border-accent ring-2 ring-accent/60',
          dimmed ? 'opacity-30' : 'opacity-100',
        )}
      >
        <div className="flex items-center gap-2">
          <span
            className={cn('size-1.5 shrink-0 rounded-full', toneFill[graphCategoryTone[category]])}
            aria-hidden
          />
          <span className="text-micro tracking-[0.09em] text-ink-muted uppercase">
            {graphCategoryLabel[category]}
          </span>
        </div>

        <p
          className={cn(
            'mt-1.5 flex-1 leading-snug text-ink',
            isDecision ? 'text-card-title' : 'text-small font-medium',
          )}
        >
          {title}
        </p>

        {caption ? (
          <p className="numeric truncate text-micro text-ink-muted">{caption}</p>
        ) : null}
      </div>

      <Handle type="source" position={Position.Bottom} id="s-bottom" style={HANDLE_STYLE} />
      <Handle type="source" position={Position.Right} id="s-right" style={HANDLE_STYLE} />
    </>
  );
}
