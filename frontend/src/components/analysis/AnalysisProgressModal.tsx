import { useEffect } from 'react';
import { AgentPipeline } from './AgentPipeline';
import { AnalysisMetricsPanel } from './AnalysisMetricsPanel';
import { Modal } from '@/components/ui/Modal';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAnalysisRun } from '@/hooks/useAnalysisRun';

export interface AnalysisProgressModalProps {
  decisionId: string | null;
  open: boolean;
  /** Called exactly once, the moment the run reaches a real "completed"
   * status - never a fabricated timer. */
  onComplete: (decisionId: string) => void;
  onClose: () => void;
}

/**
 * Popup shown the moment "Start Stress Test" is clicked from the New
 * Decision intake flow - runs the SAME real backend pipeline
 * (`useAnalysisRun`/`useAnalysisPolling`) that `AnalysisPage` itself
 * polls, surfaced as a blocking overlay on the intake page instead of an
 * immediate navigation, so the user watches the nine specialists run
 * before landing on the completed Analysis Workspace. Every value shown
 * is the backend's own real status - nothing here is simulated.
 */
export function AnalysisProgressModal({ decisionId, open, onComplete, onClose }: AnalysisProgressModalProps) {
  const analysis = useAnalysisRun(open ? decisionId ?? undefined : undefined);

  useEffect(() => {
    if (open && decisionId && analysis.isComplete && !analysis.hasFailed) {
      onComplete(decisionId);
    }
  }, [open, decisionId, analysis.isComplete, analysis.hasFailed, onComplete]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Stress-testing your decision"
      description="REGRET ENGINE is looking for the conditions under which this decision could fail."
      size="lg"
      dismissOnBackdrop={false}
    >
      <div className="space-y-5">
        <AnalysisMetricsPanel run={analysis.run} isComplete={analysis.isComplete} />

        <AgentPipeline
          statuses={analysis.run?.stage_statuses ?? {}}
          activeAgentId={analysis.run?.current_stage ?? null}
        />

        {analysis.triggerState === 'trigger-failed' ? (
          <ErrorState
            size="inline"
            title="Could not start the analysis"
            description={analysis.triggerError?.message}
          />
        ) : null}

        {analysis.isStalled ? (
          <ErrorState
            size="inline"
            title="Lost connection to the backend"
            description={analysis.error?.message ?? 'Could not reach the analysis backend.'}
            action={
              <button
                type="button"
                onClick={() => analysis.retry()}
                className="text-small font-medium text-accent-ink underline-offset-4 hover:underline"
              >
                Retry
              </button>
            }
          />
        ) : null}

        {analysis.hasFailed ? (
          <ErrorState
            size="inline"
            title="Analysis could not be completed"
            description={analysis.run?.error_message ?? 'The analysis run failed.'}
          />
        ) : null}
      </div>
    </Modal>
  );
}
