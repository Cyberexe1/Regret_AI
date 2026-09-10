import { useState, type FormEvent } from 'react';
import { TriangleAlert } from 'lucide-react';
import type { ExperimentOutcome } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { useSubmitExperimentResult } from '@/hooks/useSubmitExperimentResult';

export interface ExperimentResultFormProps {
  experimentId: string;
  onSubmitted: (reevaluationId: string) => void;
}

const OUTCOME_OPTIONS: { value: ExperimentOutcome; label: string }[] = [
  { value: 'success', label: 'Success' },
  { value: 'failure', label: 'Failure' },
  { value: 'partial', label: 'Partial' },
  { value: 'inconclusive', label: 'Inconclusive' },
];

/**
 * Submits an experiment's real observed outcome to the backend
 * (`POST /experiments/{id}/results`), using the exact request contract
 * (`ExperimentResultCreate`). Measured values are entered as a single
 * "variable: value" line per metric and parsed into the backend's
 * `measured_values` dict - numbers are coerced to numbers, everything
 * else stays a string, matching the backend's own accepted value types.
 */
export function ExperimentResultForm({ experimentId, onSubmitted }: ExperimentResultFormProps) {
  const [outcome, setOutcome] = useState<ExperimentOutcome>('success');
  const [summary, setSummary] = useState('');
  const [measuredValuesText, setMeasuredValuesText] = useState('');
  const submission = useSubmitExperimentResult();

  const parseMeasuredValues = (): Record<string, string | number | boolean> => {
    const values: Record<string, string | number | boolean> = {};
    for (const line of measuredValuesText.split('\n')) {
      const [key, ...rest] = line.split(':');
      if (!key || rest.length === 0) continue;
      const rawValue = rest.join(':').trim();
      const numeric = Number(rawValue);
      values[key.trim()] = rawValue !== '' && !Number.isNaN(numeric) ? numeric : rawValue;
    }
    return values;
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!summary.trim()) return;

    const response = await submission.submit(experimentId, {
      outcome,
      summary,
      measured_values: parseMeasuredValues(),
    });

    if (response) onSubmitted(response.reevaluation_id);
  };

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="space-y-5">
      <Select
        label="Outcome"
        required
        options={OUTCOME_OPTIONS}
        value={outcome}
        onChange={(event) => setOutcome(event.target.value as ExperimentOutcome)}
      />

      <Textarea
        label="Summary"
        required
        rows={4}
        placeholder="What actually happened when you ran this experiment?"
        value={summary}
        onChange={(event) => setSummary(event.target.value)}
      />

      <Textarea
        label="Measured values"
        hint="One per line, as 'variable: value' - e.g. Repeat-order rate: 18"
        rows={3}
        placeholder="Repeat-order rate: 18"
        value={measuredValuesText}
        onChange={(event) => setMeasuredValuesText(event.target.value)}
      />

      {submission.error ? (
        <div className="flex items-start gap-2.5 rounded-xl border border-danger-line bg-panel-danger px-4 py-3 text-small text-danger-ink">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            {submission.error.message}
            {submission.error.requestId ? ` (Request ID: ${submission.error.requestId})` : ''}
          </span>
        </div>
      ) : null}

      <Button type="submit" variant="primary" loading={submission.isSubmitting} disabled={!summary.trim()}>
        Submit result
      </Button>
    </form>
  );
}
