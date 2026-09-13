import { ContextField } from './ContextField';

export interface DynamicContextValues {
  desiredOutcome: string;
  constraintsText: string;
  beliefs: string;
  uncertainties: string;
  alternatives: string;
}

export interface DynamicContextSectionProps {
  values: DynamicContextValues;
  onChange: <K extends keyof DynamicContextValues>(key: K, value: DynamicContextValues[K]) => void;
}

/**
 * The MINIMAL universal "Context" system (Step 26 section 3) - exactly
 * five always-optional questions, replacing Step 25's larger six-field
 * block (which also included "commitment," now progressively disclosed
 * via `SmartContextChips` instead - see Step 26 section 7). These five
 * are the ONLY context questions shown by default for every category,
 * including "Other"/unknown decisions (section 6's universal fallback)
 * - REGRET's own Decision Analyzer discovers everything else.
 */
export function DynamicContextSection({ values, onChange }: DynamicContextSectionProps) {
  return (
    <div className="space-y-4">
      <ContextField
        label="What would make this decision successful?"
        placeholder="What would make this decision successful?"
        rows={2}
        value={values.desiredOutcome}
        onChange={(value) => onChange('desiredOutcome', value)}
      />

      <ContextField
        label="What could realistically limit this decision?"
        placeholder="What could realistically limit this decision?"
        rows={2}
        value={values.constraintsText}
        onChange={(value) => onChange('constraintsText', value)}
      />

      <ContextField
        label="What are you currently assuming?"
        placeholder="What are you currently assuming?"
        rows={2}
        value={values.beliefs}
        onChange={(value) => onChange('beliefs', value)}
      />

      <ContextField
        label="What are you least sure about?"
        placeholder="What are you least sure about?"
        rows={2}
        value={values.uncertainties}
        onChange={(value) => onChange('uncertainties', value)}
      />

      <ContextField
        label="What else could you do?"
        placeholder="What else could you do?"
        rows={2}
        value={values.alternatives}
        onChange={(value) => onChange('alternatives', value)}
      />
    </div>
  );
}
