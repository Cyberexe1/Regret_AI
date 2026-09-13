import { useState } from 'react';
import { Check, Pencil } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import type { ApiDecisionSnapshot, InterviewReadinessLevel } from '@/api/types';
import { READINESS_LABEL, READINESS_TONE } from '@/lib/interviewReadiness';
import { composeSnapshotNotes } from '@/lib/interviewSnapshot';

export interface InterviewSnapshotSummaryProps {
  snapshot: ApiDecisionSnapshot;
  readiness: InterviewReadinessLevel;
  /** Persists an edited notes string against the real decision (`PATCH
   * /decisions/{id}` with `beliefs`) - REGRET ENGINE 2.0, Step 27's own
   * "edit the snapshot before stress-testing" requirement. Resolves once
   * saved; rejects (and the component keeps the edit visible) on error. */
  onSaveNotes: (notes: string) => Promise<void>;
}

/**
 * Read-only recap of what the Adaptive Decision Interview discovered,
 * shown once it completes or is skipped (spec section 16) - deliberately
 * NOT another form to fill out: the interview already did that work.
 * The only thing a user can still change here is the free-text "Notes"
 * REGRET will read alongside the decision - everything else is the
 * interview's own structured findings, shown for transparency.
 */
export function InterviewSnapshotSummary({
  snapshot,
  readiness,
  onSaveNotes,
}: InterviewSnapshotSummaryProps) {
  const [editing, setEditing] = useState(false);
  const [notes, setNotes] = useState(() => composeSnapshotNotes(snapshot));
  const [draft, setDraft] = useState(notes);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const startEditing = () => {
    setDraft(notes);
    setSaveError(null);
    setEditing(true);
  };

  const cancelEditing = () => {
    setDraft(notes);
    setSaveError(null);
    setEditing(false);
  };

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await onSaveNotes(draft);
      setNotes(draft);
      setEditing(false);
    } catch {
      setSaveError('Could not save your edit. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="eyebrow">What REGRET understood</p>
        <Badge tone={READINESS_TONE[readiness]} size="sm" dot>
          {READINESS_LABEL[readiness]}
        </Badge>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <SummaryField title="Goal" value={snapshot.goal} />
        <SummaryField title="Constraints" values={snapshot.constraints} />
        <SummaryField title="Uncertainties" values={snapshot.uncertainties} />
        <SummaryField title="Alternatives" values={snapshot.alternatives} />
      </div>

      <div className="mt-5 border-t border-hairline pt-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-small font-medium text-ink">Notes for REGRET</p>
          {!editing ? (
            <Button variant="ghost" size="sm" leftIcon={Pencil} onClick={startEditing}>
              Edit
            </Button>
          ) : null}
        </div>

        {editing ? (
          <div className="mt-2 space-y-2">
            <Textarea
              aria-label="Notes for REGRET"
              rows={4}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            {saveError ? <p className="text-small text-danger-ink">{saveError}</p> : null}
            <div className="flex items-center gap-2">
              <Button size="sm" leftIcon={Check} loading={saving} onClick={() => void save()}>
                Save
              </Button>
              <Button variant="ghost" size="sm" disabled={saving} onClick={cancelEditing}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <p className="mt-2 whitespace-pre-line text-small text-ink-secondary">
            {notes || 'Nothing added yet.'}
          </p>
        )}
      </div>
    </div>
  );
}

function SummaryField({ title, value, values }: { title: string; value?: string | null; values?: string[] }) {
  const items = values ?? (value ? [value] : []);
  return (
    <div>
      <p className="text-micro font-medium tracking-[0.08em] text-ink-muted uppercase">{title}</p>
      {items.length > 0 ? (
        <ul className="mt-1 space-y-1">
          {items.slice(0, 4).map((item) => (
            <li key={item} className="text-small text-ink-secondary">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-small text-ink-muted">Not discussed.</p>
      )}
    </div>
  );
}
