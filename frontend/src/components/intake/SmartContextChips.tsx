import { useEffect, useState } from 'react';
import { Plus, X } from 'lucide-react';
import { chipsForCategories, type ContextChip } from '@/data/decisionTypes';
import { cn } from '@/lib/cn';
import type { DecisionCategory, RiskTolerance } from '@/types';
import {
  CommitmentField,
  FinancialCommitmentField,
  LocationField,
  RiskToleranceField,
  TimingField,
} from './ConstraintFields';
import { ContextField } from './ContextField';

export interface SmartContextChipsValues {
  budget: string;
  timeline: string;
  location: string;
  riskTolerance: RiskTolerance;
  commitment: string;
  extraDetails: Record<string, string>;
}

export interface SmartContextChipsProps {
  categories: DecisionCategory[];
  values: SmartContextChipsValues;
  onChangeConstraint: (key: 'budget' | 'timeline' | 'location' | 'riskTolerance', value: string) => void;
  onChangeCommitment: (value: string) => void;
  onChangeExtraDetail: (id: string, value: string) => void;
}

/** Whether a chip's field currently has a real value - used only to
 * pre-select chips whose field was already filled (e.g. via "Try an
 * example"), so a field a user already populated is never hidden behind
 * an unselected chip. NOT used to drive ongoing selection state - a
 * field must stay revealed while a user is actively clearing/retyping
 * it, so selection itself is tracked separately (see `selectedChipIds`
 * below). */
function chipHasValue(chip: ContextChip, values: SmartContextChipsValues): boolean {
  switch (chip.kind) {
    case 'financial':
      return values.budget.trim().length > 0;
    case 'timing':
      return values.timeline.trim().length > 0;
    case 'location':
      return values.location.trim().length > 0;
    case 'risk':
      return values.riskTolerance !== 'balanced';
    case 'commitment':
      return values.commitment.trim().length > 0;
    case 'note':
      return Boolean(values.extraDetails[chip.id]?.trim());
  }
}

/**
 * "Anything else that matters?" (Step 26 section 5) - suggests chips
 * relevant to the selected categories; clicking one reveals exactly the
 * field it represents, right below the chip row. Deselecting a chip
 * hides the field again but never discards what was typed into it, so
 * toggling a chip off and back on restores the same text.
 *
 * Never a hard requirement and never AI-generated - this is the
 * "lightweight configuration" fallback spec section 20 asks for
 * (`@/data/decisionTypes`'s `contextChipsByCategory`), kept ready to be
 * swapped for backend-driven suggestions later without changing this
 * component's shape.
 */
export function SmartContextChips({
  categories,
  values,
  onChangeConstraint,
  onChangeCommitment,
  onChangeExtraDetail,
}: SmartContextChipsProps) {
  const chips = chipsForCategories(categories);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(chips.filter((chip) => chipHasValue(chip, values)).map((chip) => chip.id)),
  );

  // Whenever the selected categories change (or on first mount), fold in
  // any newly-relevant chip whose field already has a real value (e.g.
  // "Try an example" populated it) - never removes a chip the user
  // explicitly selected, even if its category is later deselected, so a
  // field they're mid-typing into never disappears out from under them.
  useEffect(() => {
    setSelectedIds((current) => {
      const withValue = chips.filter((chip) => chipHasValue(chip, values)).map((chip) => chip.id);
      if (withValue.every((id) => current.has(id))) return current;
      return new Set([...current, ...withValue]);
    });
    // Only re-derive when the category set itself changes - value edits
    // must never auto-toggle a chip back on/off while the user types.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categories.join('|')]);

  if (chips.length === 0) return null;

  const toggle = (chip: ContextChip) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(chip.id)) {
        next.delete(chip.id);
        clearChip(chip, onChangeConstraint, onChangeCommitment, onChangeExtraDetail);
      } else {
        next.add(chip.id);
      }
      return next;
    });
  };

  return (
    <div>
      <p className="text-small font-medium text-ink">Anything else that matters?</p>
      <p className="mt-1 text-small text-ink-muted">
        Select what's relevant. Everything else stays out of the way.
      </p>

      <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Anything else that matters?">
        {chips.map((chip) => (
          <ChipToggle
            key={chip.id}
            chip={chip}
            selected={selectedIds.has(chip.id)}
            onToggle={() => toggle(chip)}
          />
        ))}
      </div>

      {chips.some((chip) => selectedIds.has(chip.id)) ? (
        <div className="mt-4 space-y-4">
          {chips
            .filter((chip) => selectedIds.has(chip.id))
            .map((chip) => (
              <RevealedChipField
                key={chip.id}
                chip={chip}
                categories={categories}
                values={values}
                onChangeConstraint={onChangeConstraint}
                onChangeCommitment={onChangeCommitment}
                onChangeExtraDetail={onChangeExtraDetail}
              />
            ))}
        </div>
      ) : null}
    </div>
  );
}

function clearChip(
  chip: ContextChip,
  onChangeConstraint: SmartContextChipsProps['onChangeConstraint'],
  onChangeCommitment: SmartContextChipsProps['onChangeCommitment'],
  onChangeExtraDetail: SmartContextChipsProps['onChangeExtraDetail'],
): void {
  switch (chip.kind) {
    case 'financial':
      onChangeConstraint('budget', '');
      return;
    case 'timing':
      onChangeConstraint('timeline', '');
      return;
    case 'location':
      onChangeConstraint('location', '');
      return;
    case 'risk':
      onChangeConstraint('riskTolerance', 'balanced');
      return;
    case 'commitment':
      onChangeCommitment('');
      return;
    case 'note':
      onChangeExtraDetail(chip.id, '');
  }
}

function ChipToggle({
  chip,
  selected,
  onToggle,
}: {
  chip: ContextChip;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onToggle}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-small font-medium transition-colors duration-150',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
        selected
          ? 'border-accent-line bg-panel-accent text-accent-ink'
          : 'border-hairline bg-surface-inset text-ink-secondary hover:border-hairline-strong hover:bg-surface-raised',
      )}
    >
      {selected ? <X className="size-3.5 shrink-0" aria-hidden /> : <Plus className="size-3.5 shrink-0" aria-hidden />}
      {chip.label}
    </button>
  );
}

function RevealedChipField({
  chip,
  categories,
  values,
  onChangeConstraint,
  onChangeCommitment,
  onChangeExtraDetail,
}: {
  chip: ContextChip;
  categories: DecisionCategory[];
  values: SmartContextChipsValues;
  onChangeConstraint: SmartContextChipsProps['onChangeConstraint'];
  onChangeCommitment: SmartContextChipsProps['onChangeCommitment'];
  onChangeExtraDetail: SmartContextChipsProps['onChangeExtraDetail'];
}) {
  switch (chip.kind) {
    case 'financial':
      return (
        <FinancialCommitmentField
          categories={categories}
          value={values.budget}
          onChange={(value) => onChangeConstraint('budget', value)}
        />
      );
    case 'timing':
      return <TimingField value={values.timeline} onChange={(value) => onChangeConstraint('timeline', value)} />;
    case 'location':
      return (
        <LocationField
          categories={categories}
          value={values.location}
          onChange={(value) => onChangeConstraint('location', value)}
        />
      );
    case 'risk':
      return (
        <RiskToleranceField
          value={values.riskTolerance}
          onChange={(value) => onChangeConstraint('riskTolerance', value)}
        />
      );
    case 'commitment':
      return <CommitmentField value={values.commitment} onChange={onChangeCommitment} />;
    case 'note':
      return (
        <ContextField
          label={chip.fieldLabel ?? chip.label}
          placeholder={chip.fieldPlaceholder ?? ''}
          rows={2}
          value={values.extraDetails[chip.id] ?? ''}
          onChange={(value) => onChangeExtraDetail(chip.id, value)}
        />
      );
  }
}
