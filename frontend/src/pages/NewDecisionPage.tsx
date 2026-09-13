import { useMemo, useState, type FormEvent } from 'react';
import { Globe, MessageCircleQuestion, TriangleAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  DecisionTypeSelector,
  EvidenceDropzone,
  ExampleDecisionPicker,
  IntakeActionBar,
  IntakeProgress,
  IntakeSection,
  InterviewConsole,
  InterviewSnapshotSummary,
} from '@/components/intake';
import { AnalysisProgressModal } from '@/components/analysis';
import { CrossDecisionPatternsPanel, HistoricalInsightsPanel } from '@/components/report';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { decisionsApi } from '@/api';
import { inferDecisionCategory, type ExampleDecision } from '@/data/decisionTypes';
import { INTAKE_SECTION_IDS, resolveIntakeSteps } from '@/data/intake';
import { analysisPath } from '@/data/navigation';
import { useCrossDecisionPatterns } from '@/hooks/useCrossDecisionPatterns';
import { useDecisionIntake } from '@/hooks/useDecisionIntake';
import { useDecisionSubmission } from '@/hooks/useDecisionSubmission';
import { useHistoricalContextPreview } from '@/hooks/useHistoricalContextPreview';
import { useInterview } from '@/hooks/useInterview';
import { buildCrossDecisionPatternRows } from '@/lib/buildCrossDecisionPatterns';
import { buildDecisionCreatePayload } from '@/lib/decisionPayload';
import { describeApiError } from '@/lib/apiError';
import { EMPTY_HISTORICAL_SUMMARY } from '@/lib/buildHistoricalContext';

/**
 * REGRET ENGINE's decision intake (Step 26 "Smart Minimal Intake",
 * reworked in Step 27 - "Adaptive Decision Interview Agent"). Two
 * visible stages, in strict visual-hierarchy order: THE DECISION first
 * and largest, then a short back-and-forth CONVERSATION that discovers
 * context adaptively - never a long, always-visible form of context
 * questions. "Tell REGRET what you're considering. It will figure out
 * what matters" is the target feel (spec section 1), not "fill out a
 * large decision form."
 *
 * The decision itself is created as soon as the interview starts (not
 * at final submission) so the interview has a real `decision_id` to
 * attach its findings to - `useDecisionSubmission.submit` is then
 * called with that SAME id at the end, so it only uploads evidence
 * rather than creating a second, orphaned decision.
 */
export function NewDecisionPage() {
  const navigate = useNavigate();
  const {
    draft,
    canSubmit,
    evidenceErrors,
    setField,
    setCategories,
    applyExample,
    addFiles,
    removeFile,
  } = useDecisionIntake();
  const submission = useDecisionSubmission();
  const interview = useInterview();
  const [decisionId, setDecisionId] = useState<string | null>(null);
  const [startingDecision, setStartingDecision] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [skippedInterview, setSkippedInterview] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [progressModalOpen, setProgressModalOpen] = useState(false);
  const historicalPreview = useHistoricalContextPreview(draft.decision);
  const crossDecisionPatterns = useCrossDecisionPatterns();
  const patternRows = buildCrossDecisionPatternRows(crossDecisionPatterns.data ?? []);
  const inferredCategory = useMemo(() => inferDecisionCategory(draft.decision), [draft.decision]);

  const interviewFinished = interview.stage === 'completed';
  const contextSettled = interviewFinished || skippedInterview;
  const isSubmitting = submission.stage === 'creating-decision' || submission.stage === 'uploading-evidence';
  const readyToSubmit = canSubmit && decisionId !== null && contextSettled;

  const stepsWithInterview = useMemo(
    () => resolveIntakeSteps(draft, contextSettled),
    [draft, contextSettled],
  );

  const startInterview = async () => {
    if (!canSubmit || startingDecision) return;
    setStartError(null);
    setSkippedInterview(false);

    let id = decisionId;
    if (!id) {
      setStartingDecision(true);
      try {
        const created = await decisionsApi.createDecision(buildDecisionCreatePayload(draft));
        id = created.id;
        setDecisionId(id);
      } catch (error) {
        setStartError(describeApiError(error).message);
        setStartingDecision(false);
        return;
      }
      setStartingDecision(false);
    }

    await interview.start(id, draft.categories);
  };

  const saveSnapshotNotes = async (notes: string) => {
    if (!decisionId) return;
    await decisionsApi.updateDecision(decisionId, { beliefs: notes || null });
  };

  const startStressTest = async () => {
    if (!readyToSubmit || isSubmitting || !decisionId) return;
    setSubmitError(null);

    const submittedDecisionId = await submission.submit(draft, decisionId);
    if (!submittedDecisionId) {
      setSubmitError(submission.error?.message ?? 'Could not start the stress test. Please try again.');
      return;
    }

    // Evidence uploads that failed are reported, but never block moving on -
    // the decision itself already exists and analysis can still run. Rather
    // than navigating away immediately, open the live progress popup and
    // only leave this page once the real pipeline actually completes.
    setProgressModalOpen(true);
  };

  const onAnalysisComplete = (completedDecisionId: string) => {
    setProgressModalOpen(false);
    navigate(analysisPath(completedDecisionId));
  };

  const onFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void startStressTest();
  };

  const onSelectExample = (example: ExampleDecision) => {
    // The decision statement (and everything an example would overwrite)
    // is locked once the interview has actually started - matches the
    // textarea's own `disabled={decisionId !== null}` above.
    if (decisionId !== null) return;
    applyExample({
      decision: example.decision,
      categories: example.categories,
      desiredOutcome: example.desiredOutcome ?? '',
      constraintsText: example.constraints ?? '',
      beliefs: example.beliefs ?? '',
      uncertainties: example.uncertainties ?? '',
      alternatives: example.alternatives ?? '',
      commitment: example.commitment ?? '',
      constraints: {
        budget: example.financialCommitment ?? '',
        timeline: example.timing ?? '',
        location: example.location ?? '',
        riskTolerance: draft.constraints.riskTolerance,
      },
    });
    document.getElementById(INTAKE_SECTION_IDS.decision)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <PageContainer
      width="default"
      title="What are you about to commit to?"
      description="Tell REGRET what you're considering. It will figure out what matters."
    >
      <IntakeProgress steps={stepsWithInterview} />

      {submitError ? (
        <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-danger-line bg-panel-danger px-5 py-4 text-small text-danger-ink">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          {submitError}
        </div>
      ) : null}

      <form onSubmit={onFormSubmit} noValidate className="mt-8 space-y-5">
        <IntakeSection
          id={INTAKE_SECTION_IDS.decision}
          phase="01 · Decision"
          title="The decision"
          description="Write the decision exactly as you're considering it - including what you would commit, change, accept, or give up."
          className="mx-[15px]"
        >
          <div className="space-y-5">
            <Textarea
              aria-label="The decision"
              rows={4}
              maxLength={600}
              showCount
              placeholder="Should I accept the software engineering offer from Company A?"
              className="md:text-body-lg"
              value={draft.decision}
              disabled={decisionId !== null}
              onChange={(event) => setField('decision', event.target.value)}
            />

            {decisionId === null ? <ExampleDecisionPicker onSelect={onSelectExample} /> : null}

            <DecisionTypeSelector
              value={draft.categories}
              onChange={setCategories}
              inferredCategory={inferredCategory}
            />
          </div>
        </IntakeSection>

        <IntakeSection
          id={INTAKE_SECTION_IDS.context}
          phase="02 · Context"
          title="Context"
          description="REGRET will ask exactly what it needs to know - nothing more."
          className="mx-[15px]"
        >
          {startError ? (
            <div className="mb-4 flex items-start gap-2.5 rounded-lg border border-danger-line bg-panel-danger px-4 py-3 text-small text-danger-ink">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              {startError}
            </div>
          ) : null}

          {decisionId === null ? (
            <InterviewStartPanel
              canStart={canSubmit}
              starting={startingDecision}
              retrying={startError !== null}
              onStart={() => void startInterview()}
            />
          ) : interviewFinished ? (
            <InterviewSnapshotSummary
              snapshot={interview.snapshot!}
              readiness={interview.readiness ?? 'early'}
              onSaveNotes={saveSnapshotNotes}
            />
          ) : skippedInterview ? (
            <p className="text-small text-ink-muted">
              Continuing without the interview - REGRET's own analysis will discover what's missing.
            </p>
          ) : interview.stage === 'idle' ? (
            <InterviewStartPanel
              canStart={canSubmit}
              starting={false}
              retrying
              error={interview.error?.message}
              onStart={() => void startInterview()}
              onSkip={() => setSkippedInterview(true)}
            />
          ) : interview.stage === 'starting' ? (
            <p role="status" className="py-6 text-center text-small text-ink-muted">
              Starting the interview…
            </p>
          ) : (
            <InterviewConsole
              interview={interview}
              onSend={(message) => void interview.respond(message)}
              onSkip={() => void interview.skip()}
              onContinueToStressTest={() => void interview.complete()}
            />
          )}
        </IntakeSection>

        {historicalPreview.summary?.found || historicalPreview.isLoading ? (
          <IntakeSection
            id={INTAKE_SECTION_IDS.historicalContext}
            phase="02 · Context"
            title="Relevant from your past decisions"
            description="Deterministic similarity from your own decision history - background context, not a verdict on this decision."
          >
            <HistoricalInsightsPanel
              summary={historicalPreview.summary ?? EMPTY_HISTORICAL_SUMMARY}
              isLoading={historicalPreview.isLoading}
              compact
            />
          </IntakeSection>
        ) : null}

        {patternRows.length > 0 ? (
          <IntakeSection
            id="relevant-learnings"
            phase="02 · Context"
            title="Relevant learnings from your history"
            description="Recurring patterns across your OWN past decisions - background awareness, never a verdict on this specific decision. Current evidence you provide above always matters more."
          >
            <CrossDecisionPatternsPanel rows={patternRows} isLoading={crossDecisionPatterns.isLoading} />
          </IntakeSection>
        ) : null}

        <IntakeSection
          id={INTAKE_SECTION_IDS.evidence}
          phase="03 · Evidence"
          title="Evidence you already have"
          description="Give REGRET what you already know. Evidence can support, contradict, or leave your reasoning uncertain."
          className="mx-[15px]"
        >
          <div className="space-y-6">
            <EvidenceDropzone
              files={draft.evidence}
              errors={evidenceErrors}
              onAdd={addFiles}
              onRemove={removeFile}
            />

            <Input
              label="Add a website or source"
              labelAside="Optional"
              type="url"
              inputMode="url"
              icon={Globe}
              placeholder="https://..."
              value={draft.sourceUrl}
              onChange={(event) => setField('sourceUrl', event.target.value)}
            />
          </div>
        </IntakeSection>

        <IntakeActionBar
          id={INTAKE_SECTION_IDS.submit}
          canSubmit={readyToSubmit && !isSubmitting}
          submitting={isSubmitting}
          onSubmit={() => void startStressTest()}
        />
      </form>

      <AnalysisProgressModal
        decisionId={decisionId}
        open={progressModalOpen}
        onComplete={onAnalysisComplete}
        onClose={() => setProgressModalOpen(false)}
      />
    </PageContainer>
  );
}

interface InterviewStartPanelProps {
  canStart: boolean;
  starting: boolean;
  retrying?: boolean;
  error?: string;
  onStart: () => void;
  onSkip?: () => void;
}

/**
 * "Start interview" CTA (spec section 20) - shown before the
 * conversation begins, and again (as a retry) if starting it failed.
 * Never a hard gate: `onSkip` (only offered once a start has actually
 * been attempted) lets a user continue with just the decision
 * statement, matching the rest of this form's "nothing is ever
 * required except the decision" philosophy.
 */
function InterviewStartPanel({ canStart, starting, retrying, error, onStart, onSkip }: InterviewStartPanelProps) {
  return (
    <div className="rounded-xl border border-dashed border-hairline-strong bg-surface-inset px-5 py-6 text-center">
      <span className="mx-auto flex size-10 items-center justify-center rounded-lg border border-hairline bg-surface-raised text-ink-muted">
        <MessageCircleQuestion className="size-4.5" aria-hidden />
      </span>
      <p className="mt-3 text-card-title text-ink">
        {retrying ? "REGRET couldn't continue the interview" : "Let REGRET ask what it needs to know"}
      </p>
      <p className="mx-auto mt-1.5 max-w-sm text-small text-ink-secondary">
        {error ??
          'A short back-and-forth, not a form - REGRET will only ask about what actually matters for this decision.'}
      </p>
      <div className="mt-4 flex items-center justify-center gap-3">
        <Button size="sm" loading={starting} disabled={!canStart} onClick={onStart}>
          {retrying ? 'Try again' : 'Start interview'}
        </Button>
        {retrying && onSkip ? (
          <Button variant="ghost" size="sm" onClick={onSkip}>
            Continue without it
          </Button>
        ) : null}
      </div>
    </div>
  );
}

