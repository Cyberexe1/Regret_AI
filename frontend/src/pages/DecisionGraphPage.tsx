import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, FileText, Workflow } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { DecisionNotFound } from '@/components/DecisionNotFound';
import { PageContainer } from '@/components/layout/PageContainer';
import { GraphLegend, NodeDetailPanel } from '@/components/graph';
import { buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { decisionPath } from '@/data/navigation';
import { useDecisionById } from '@/hooks/useDecisionById';
import { useDecisionReportData } from '@/hooks/useDecisionReportData';
import { buildDecisionGraph } from '@/lib/buildDecisionGraph';
import { cn } from '@/lib/cn';

const DecisionGraphCanvas = lazy(async () => {
  const module = await import('@/components/graph/DecisionGraphCanvas');
  return { default: module.DecisionGraphCanvas };
});

function CanvasFallback() {
  return (
    <div className="h-full w-full p-6" role="status" aria-label="Loading dependency graph">
      <Skeleton shape="block" className="size-full" />
    </div>
  );
}

export function DecisionGraphPage() {
  const { id } = useParams<{ id: string }>();
  const decisionState = useDecisionById(id);
  const reportState = useDecisionReportData(id);

  const graph = useMemo(() => {
    if (!decisionState.data || !reportState.data) return undefined;
    return buildDecisionGraph(
      decisionState.data,
      reportState.data.assumptions,
      reportState.data.blindspots,
      reportState.data.thresholds,
      reportState.data.experiments,
    );
  }, [decisionState.data, reportState.data]);

  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedId(graph?.defaultNodeId ?? null);
  }, [graph?.decisionId, graph?.defaultNodeId]);

  if (!id) return <DecisionNotFound id={id} />;

  if (decisionState.status === 'error') {
    if (decisionState.error?.message.toLowerCase().includes('not found')) {
      return <DecisionNotFound id={id} />;
    }
    return (
      <PageContainer eyebrow="Dependency graph" title="Decision graph">
        <ErrorState title="Unable to load this decision" description={decisionState.error?.message} />
      </PageContainer>
    );
  }

  if (decisionState.isLoading || reportState.isLoading || !decisionState.data) {
    return (
      <PageContainer eyebrow="Dependency graph" title="Loading…" width="narrow">
        <div role="status" aria-label="Loading">
          <Skeleton shape="block" className="h-96 w-full" />
        </div>
      </PageContainer>
    );
  }

  const decision = decisionState.data;

  if (reportState.status === 'error') {
    return (
      <PageContainer eyebrow="Dependency graph" title={decision.title}>
        <ErrorState
          title="Unable to load the analysis for this decision"
          description={reportState.error?.message}
          action={
            <button
              type="button"
              onClick={reportState.refetch}
              className="text-small font-medium text-accent-ink underline-offset-4 hover:underline"
            >
              Retry
            </button>
          }
        />
      </PageContainer>
    );
  }

  if (!graph || graph.nodes.length <= 1) {
    return (
      <PageContainer eyebrow="Dependency graph" title={decision.title} width="narrow">
        <EmptyState
          icon={Workflow}
          title="No dependency graph yet"
          description="A graph is built from a completed stress test. This decision has not produced one, so there is nothing to map."
          action={
            <Link to={decisionPath(decision.id)} className={buttonClasses({ variant: 'secondary', size: 'sm' })}>
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
      description="Every assumption, blindspot and threshold the decision depends on. Hover to trace a branch, select a node to inspect it."
      actions={
        <Link to={decisionPath(decision.id)} className={cn(buttonClasses({ variant: 'secondary', size: 'sm' }))}>
          <FileText className="size-4" aria-hidden />
          Decision report
        </Link>
      }
    >
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem] xl:items-start">
        <div className="overflow-hidden rounded-xl border border-hairline bg-surface-inset">
          <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-hairline px-5 py-4 md:px-6">
            <GraphLegend />
            <p className="text-small text-ink-muted">Drag to pan · zoom with the controls</p>
          </div>

          <div className="h-[58vh] min-h-96 lg:h-[66vh]">
            <Suspense fallback={<CanvasFallback />}>
              <DecisionGraphCanvas graph={graph} selectedId={selectedId} onSelect={setSelectedId} />
            </Suspense>
          </div>
        </div>

        <div className="xl:sticky xl:top-[calc(var(--header-offset)+0.75rem)]">
          <NodeDetailPanel node={selectedNode} />
        </div>
      </div>
    </PageContainer>
  );
}
