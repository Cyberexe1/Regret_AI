import { useEffect, useState } from 'react';
import { ArrowLeft, FileText } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import { DecisionGraphCanvas } from '@/components/graph/DecisionGraphCanvas';
import { GraphLegend, NodeDetailPanel } from '@/components/graph';
import { buttonClasses } from '@/components/ui/Button';
import { Card, CardDescription, CardTitle } from '@/components/ui/Card';
import { findDecisionGraph } from '@/data/decisionGraph';
import { decisionPath, ROUTES } from '@/data/navigation';
import { useDecision } from '@/hooks/useDecisions';
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

  if (!decision) {
    return (
      <PageContainer eyebrow="Decision" title="Decision not found" width="narrow">
        <Card padding="lg" className="space-y-4">
          <CardTitle>No decision matches this identifier</CardTitle>
          <CardDescription>
            The reference <span className="numeric text-ink">{id}</span> is not in this workspace.
          </CardDescription>
          <Link
            to={ROUTES.decisions}
            className={buttonClasses({ variant: 'secondary', size: 'sm' })}
          >
            <ArrowLeft className="size-4" aria-hidden />
            Back to decision history
          </Link>
        </Card>
      </PageContainer>
    );
  }

  if (!graph) {
    return (
      <PageContainer eyebrow="Dependency graph" title={decision.title} width="narrow">
        <Card padding="lg" className="space-y-4">
          <CardTitle>No dependency graph yet</CardTitle>
          <CardDescription>
            A graph is built from a completed stress test. This decision has not produced one, so
            there is nothing to map.
          </CardDescription>
          <Link
            to={decisionPath(decision.id)}
            className={buttonClasses({ variant: 'secondary', size: 'sm' })}
          >
            <ArrowLeft className="size-4" aria-hidden />
            Back to the decision
          </Link>
        </Card>
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
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
        <div className="overflow-hidden rounded-xl border border-hairline bg-surface-inset">
          <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-hairline px-5 py-3.5">
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

        <div className="lg:sticky lg:top-[calc(var(--topbar-height)+1.5rem)]">
          <NodeDetailPanel node={selectedNode} />
        </div>
      </div>
    </PageContainer>
  );
}
