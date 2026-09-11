import { useState, type FormEvent } from 'react';
import { Globe, TriangleAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  ConstraintFields,
  EvidenceDropzone,
  IntakeActionBar,
  IntakeProgress,
  IntakeSection,
} from '@/components/intake';
import { HistoricalInsightsPanel } from '@/components/report';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { INTAKE_SECTION_IDS } from '@/data/intake';
import { analysisPath } from '@/data/navigation';
import { useDecisionIntake } from '@/hooks/useDecisionIntake';
import { useDecisionSubmission } from '@/hooks/useDecisionSubmission';
import { useHistoricalContextPreview } from '@/hooks/useHistoricalContextPreview';
import { EMPTY_HISTORICAL_SUMMARY } from '@/lib/buildHistoricalContext';

export function NewDecisionPage() {
  const navigate = useNavigate();
  const {
    draft,
    steps,
    canSubmit,
    evidenceErrors,
    setField,
    setConstraint,
    addFiles,
    removeFile,
  } = useDecisionIntake();
  const submission = useDecisionSubmission();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const historicalPreview = useHistoricalContextPreview(draft.decision);

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

  return (
    <PageContainer
      width="narrow"
      eyebrow="New Decision"
      title="What are you about to commit to?"
      description="Give REGRET ENGINE enough context to discover what you may be missing."
    >
      <IntakeProgress steps={steps} />

      {submitError ? (
        <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-danger-line bg-panel-danger px-5 py-4 text-small text-danger-ink">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          {submitError}
        </div>
      ) : null}

      <form onSubmit={onFormSubmit} noValidate className="mt-10 space-y-5">
        <IntakeSection
          id={INTAKE_SECTION_IDS.decision}
          phase="01 · Decision"
          title="The decision"
          description="Write it as you would say it out loud, including the number and the commitment."
        >
          <Textarea
            aria-label="The decision"
            rows={5}
            maxLength={600}
            showCount
            placeholder="Example: Should I invest ₹5,00,000 to start a cloud kitchen in Mumbai?"
            className="md:text-body-lg"
            value={draft.decision}
            onChange={(event) => setField('decision', event.target.value)}
          />
        </IntakeSection>

        <IntakeSection
          id={INTAKE_SECTION_IDS.outcome}
          phase="02 · Context"
          title="What outcome are you trying to achieve?"
          description="The engine tests the decision against this, not against a generic definition of success."
        >
          <Textarea
            aria-label="Desired outcome"
            rows={4}
            placeholder="Describe what success looks like."
            value={draft.desiredOutcome}
            onChange={(event) => setField('desiredOutcome', event.target.value)}
          />
        </IntakeSection>

        <IntakeSection
          id={INTAKE_SECTION_IDS.constraints}
          phase="02 · Context"
          title="Constraints"
          description="What actually binds this decision. Leave anything blank if it does not apply."
        >
          <ConstraintFields constraints={draft.constraints} onChange={setConstraint} />
        </IntakeSection>

        <IntakeSection
          id={INTAKE_SECTION_IDS.beliefs}
          phase="02 · Context"
          title="What do you already believe?"
          description="These beliefs become assumptions for the stress test."
        >
          <Textarea
            aria-label="What you already believe"
            rows={4}
            placeholder="I believe this decision will work because..."
            value={draft.beliefs}
            onChange={(event) => setField('beliefs', event.target.value)}
          />
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

        <IntakeSection
          id={INTAKE_SECTION_IDS.evidence}
          phase="03 · Evidence"
          title="Evidence you already have"
          description="Anything that supports or contradicts your reasoning. The contradictions are the useful part."
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
