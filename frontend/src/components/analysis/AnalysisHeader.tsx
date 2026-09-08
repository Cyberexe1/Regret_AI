import { ActivityPulse } from './ActivityPulse';

export interface AnalysisHeaderProps {
  decisionStatement: string;
  isComplete: boolean;
}

export function AnalysisHeader({ decisionStatement, isComplete }: AnalysisHeaderProps) {
  return (
    <header>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <p className="eyebrow">Stress test</p>
        {isComplete ? null : (
          <span className="flex items-center gap-2 text-micro tracking-[0.09em] text-accent-ink uppercase">
            <ActivityPulse />
            In progress
          </span>
        )}
      </div>

      <h2 className="mt-4 text-page-title text-ink">Stress-testing your decision</h2>

      <blockquote className="mt-6 rounded-xl border border-hairline bg-surface-inset px-5 py-4 md:px-6 md:py-5">
        <p className="eyebrow">The decision</p>
        <p className="mt-2 text-section-title text-ink">{decisionStatement}</p>
      </blockquote>

      <p className="mt-5 max-w-2xl text-body text-ink-secondary">
        REGRET ENGINE is looking for the conditions under which this decision could fail.
      </p>
    </header>
  );
}
