import { useMemo, useState, type FormEvent } from 'react';
import { Globe, TriangleAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  DecisionTypeSelector,
  DynamicContextSection,
  EvidenceDropzone,
  ExampleDecisionPicker,
  IntakeActionBar,
  IntakeProgress,
  IntakeSection,
  SmartContextChips,
} from '@/components/intake';
import { CrossDecisionPatternsPanel, HistoricalInsightsPanel } from '@/components/report';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { inferDecisionCategory, type ExampleDecision } from '@/data/decisionTypes';
import { INTAKE_SECTION_IDS } from '@/data/intake';
import { analysisPath } from '@/data/navigation';
import { useCrossDecisionPatterns } from '@/hooks/useCrossDecisionPatterns';
import { useDecisionIntake } from '@/hooks/useDecisionIntake';
import { useDecisionSubmission } from '@/hooks/useDecisionSubmission';
import { useHistoricalContextPreview } from '@/hooks/useHistoricalContextPreview';
import { buildCrossDecisionPatternRows } from '@/lib/buildCrossDecisionPatterns';
import { EMPTY_HISTORICAL_SUMMARY } from '@/lib/buildHistoricalContext';

/**
 * REGRET ENGINE's "Smart Minimal Intake" (Step 26). Three visible
 * stages, in strict visual-hierarchy order (spec section 22): THE
 * DECISION first and largest, CONTEXT second (five always-optional
 * questions, never a business questionnaire), EVIDENCE third, then
 * START STRESS TEST. Everything financial/timing/location/risk/
 * commitment-related is progressively disclosed via `SmartContextChips`
 * - nothing forces the user to fill every possible decision attribute
 * (Step 25's larger, always-visible field set is deliberately replaced
 * here). A decision with zero optional context is still a complete,
 * submittable decision - REGRET's own agents discover what's missing.
 */
export function NewDecisionPage() {
  const navigate = useNavigate();
  const {
    draft,
    steps,
    canSubmit,
    evidenceErrors,
    setField,
    setCategories,
    setConstraint,
    setExtraDetail,
    applyExample,
    addFiles,
    removeFile,
  } = useDecisionIntake();
  const submission = useDecisionSubmission();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const historicalPreview = useHistoricalContextPreview(draft.decision);
  const crossDecisionPatterns = useCrossDecisionPatterns();
  const patternRows = buildCrossDecisionPatternRows(crossDecisionPatterns.data ?? []);
  const inferredCategory = useMemo(() => inferDecisionCategory(draft.decision), [draft.decision]);

  const isSubmitting = submission.stage === 'creating-decision' || submission.stage === 'uploading-evidence';

  const startStressTest = async () => {
    if (!canSubmit || isSubmitting) return;
    setSubmitError(null);

    const decisionId = await submission.submit(draft);
    if (!decisionId) {
      setSubmitError(submission.error?.message ?? 'Could not create the decision. Please try again.');
      return;
    }

    // Evidence uploads that failed are reported, but never block moving on -
    // the decision itself was created successfully and analysis can still run.
    navigate(analysisPath(decisionId));
  };

  const onFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void startStressTest();
  };

  const onSelectExample = (example: ExampleDecision) => {
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
      width="narrow"
      eyebrow="New Decision"
      title="What are you about to commit to?"
      description="Give REGRET enough context to discover what you may be missing — whatever kind of decision this is."
    >
      <IntakeProgress steps={steps} />

      {submitError ? (
        <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-danger-line bg-panel-danger px-5 py-4 text-small text-danger-ink">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          {submitError}
        </div>
      ) : null}

      <div className="mt-8">
        <ExampleDecisionPicker onSelect={onSelectExample} />
      </div>

      <form onSubmit={onFormSubmit} noValidate className="mt-8 space-y-5">
        <IntakeSection
          id={INTAKE_SECTION_IDS.decision}
          phase="01 · Decision"
          title="The decision"
          description="Write the decision exactly as you're considering it - including what you would commit, change, accept, or give up."
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
              onChange={(event) => setField('decision', event.target.value)}
            />

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
          description="That's enough to start. Add only what actually matters here - REGRET's agents will discover the rest."
        >
          <div className="space-y-6">
            <DynamicContextSection
              values={{
                desiredOutcome: draft.desiredOutcome,
                constraintsText: draft.constraintsText,
                beliefs: draft.beliefs,
                uncertainties: draft.uncertainties,
                alternatives: draft.alternatives,
              }}
              onChange={(key, value) => setField(key, value)}
            />

            <SmartContextChips
              categories={draft.categories}
              values={{
                budget: draft.constraints.budget,
                timeline: draft.constraints.timeline,
                location: draft.constraints.location,
                riskTolerance: draft.constraints.riskTolerance,
                commitment: draft.commitment,
                extraDetails: draft.extraDetails,
              }}
              onChangeConstraint={(key, value) =>
                key === 'riskTolerance'
                  ? setConstraint('riskTolerance', value as never)
                  : setConstraint(key, value)
              }
              onChangeCommitment={(value) => setField('commitment', value)}
              onChangeExtraDetail={setExtraDetail}
            />
          </div>
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
          canSubmit={canSubmit && !isSubmitting}
          submitting={isSubmitting}
          onSubmit={() => void startStressTest()}
        />
      </form>
    </PageContainer>
  );
}
