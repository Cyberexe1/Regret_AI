import type { FormEvent } from 'react';
import { Globe } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  ConstraintFields,
  EvidenceDropzone,
  IntakeActionBar,
  IntakeProgress,
  IntakeSection,
} from '@/components/intake';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { INTAKE_SECTION_IDS } from '@/data/intake';
import { ROUTES } from '@/data/navigation';
import { useDecisionIntake } from '@/hooks/useDecisionIntake';
import { saveDecisionDraft } from '@/lib/decisionDraft';

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

  const startStressTest = () => {
    if (!canSubmit) return;

    const submitted = { ...draft, submittedAt: new Date().toISOString() };

    // Stored locally and handed to the next route. No network call.
    saveDecisionDraft(submitted);
    navigate(ROUTES.analysis, { state: { draft: submitted } });
  };

  const onFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    startStressTest();
  };

  return (
    <PageContainer
      width="narrow"
      eyebrow="New Decision"
      title="What are you about to commit to?"
      description="Give REGRET ENGINE enough context to discover what you may be missing."
    >
      <IntakeProgress steps={steps} />

      <form onSubmit={onFormSubmit} noValidate className="mt-10 space-y-5">
        <IntakeSection
          id={INTAKE_SECTION_IDS.decision}
          phase="01 · Decision"
          title="The decision"
          description="Write it as you would say it out loud, including the number and the commitment."
          emphasis
        >
          <Textarea
            aria-label="The decision"
            rows={5}
            maxLength={600}
            showCount
            placeholder="Example: Should I invest ₹5,00,000 to start a cloud kitchen in Mumbai?"
            className="md:text-[1.0625rem]"
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
          canSubmit={canSubmit}
          onSubmit={startStressTest}
        />
      </form>
    </PageContainer>
  );
}
