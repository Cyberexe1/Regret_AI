import { useEffect, useState } from 'react';
import { ArrowLeft, FileText, Workflow } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { DecisionNotFound } from '@/components/DecisionNotFound';
import { PageContainer } from '@/components/layout/PageContainer';
import { DecisionGraphCanvas } from '@/components/graph/DecisionGraphCanvas';
import { GraphLegend, NodeDetailPanel } from '@/components/graph';
import { buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { findDecisionGraph } from '@/data/decisionGraph';
import { decisionPath } from '@/data/navigation';
import { useDecision } from '@/hooks/useDecision';
import { cn } from '@/lib/cn';

export function DecisionGraphPage() {
  const { id } = useParams<{ id: string }>();
  const decision = useDecision(id);
  const graph = decision ? findDecisionGraph(decision.id) : undefined;

  const [selectedId, setSelectedId] = useState<string | null>(graph?.defaultNodeId ?? null);

  // Reset the selection when navigating between graphs.
  useEffect(() => {
    setSelectedId(graph?.defaultNodeId ?? null);
  }, [graph?.decisionId, graph?.defaultNodeId]);

  if (!decision) return <DecisionNotFound id={id} />;

  if (!graph) {
    return (
      <PageContainer eyebrow="Dependency graph" title={decision.title} width="narrow">
        <EmptyState
          icon={Workflow}
          title="No dependency graph yet"
          description="A graph is built from a completed stress test. This decision has not produced one, so there is nothing to map."
          action={
            <Link
              to={decisionPath(decision.id)}
              className={buttonClasses({ variant: 'secondary', size: 'sm' })}
            >
              <ArrowLeft className="size-4" aria-hidden />
              Back to the decision
            </Link>
          }
        />
      </PageContainer>
    );
  }

  const selectedNode = graph.nodes.find((node) => node.id === selectedId) ?? null;

  return (
    <PageContainer
      eyebrow="Dependency graph"
      title="What this decision rests on"
      description="Every assumption, threshold and outcome the decision depends on. Hover to trace a branch, select a node to inspect it."
      actions={
        <Link
          to={decisionPath(decision.id)}
          className={cn(buttonClasses({ variant: 'secondary', size: 'sm' }))}
        >
          <FileText className="size-4" aria-hidden />
          Decision report
        </Link>
      }
    >
      {/* Side panel waits for xl: the canvas needs the width more than the panel does. */}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem] xl:items-start">
        <div className="overflow-hidden rounded-xl border border-hairline bg-surface-inset">
          <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-hairline px-5 py-4 md:px-6">
            <GraphLegend />
            <p className="text-small text-ink-muted">Drag to pan · zoom with the controls</p>
          </div>

          <div className="h-[58vh] min-h-96 lg:h-[66vh]">
            <DecisionGraphCanvas
              graph={graph}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
        </div>

        <div className="xl:sticky xl:top-[calc(var(--header-offset)+0.75rem)]">
          <NodeDetailPanel node={selectedNode} />
        </div>
      </div>
    </PageContainer>
  );
}
