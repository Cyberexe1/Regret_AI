import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { ArrowRight, TriangleAlert } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { InterviewMessage, InterviewState } from '@/hooks/useInterview';
import { cn } from '@/lib/cn';
import type { Tone } from '@/types';

export interface InterviewConsoleProps {
  interview: InterviewState;
  onSend: (message: string) => void;
  onSkip: () => void;
  onContinueToStressTest: () => void;
}

const READINESS_LABEL: Record<string, string> = {
  early: "We're still understanding the decision.",
  enough: 'I have enough context to stress-test this decision.',
  ready: "I've identified the main uncertainties worth testing.",
};

const READINESS_TONE: Record<string, Tone> = {
  early: 'neutral',
  enough: 'info',
  ready: 'success',
};

/**
 * The "Decision Interview Console" (REGRET ENGINE 2.0, Step 27, spec
 * sections 20-24) - deliberately NOT a full-screen generic chatbot
 * (spec section 21): a compact conversation area, a live decision-model
 * side panel, a progress indicator, and optional quick-response chips.
 * The Interview Agent never produces a verdict on the decision - only
 * REGRET's existing analysis pipeline does that, once this console
 * hands off a finished `DecisionSnapshot`.
 */
export function InterviewConsole({
  interview,
  onSend,
  onSkip,
  onContinueToStressTest,
}: InterviewConsoleProps) {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const isSubmitting = interview.stage === 'submitting' || interview.stage === 'starting';
  const isDone = interview.stage === 'ready' || interview.stage === 'completing' || interview.stage === 'completed';

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [interview.messages.length]);

  const turnNumber = interview.state?.turn_number ?? 0;
  const maxTurns = interview.state?.max_turns ?? 7;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft.trim() || isSubmitting || isDone) return;
    onSend(draft);
    setDraft('');
  };

  const pickChip = (chip: string) => {
    if (isSubmitting || isDone) return;
    onSend(chip);
    setDraft('');
  };

  return (
    <div data-testid="interview-console" className="rounded-xl border border-hairline bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-5 py-4 md:px-6">
        <div>
          <p className="eyebrow">REGRET Interview</p>
          <p className="mt-1 text-small text-ink-secondary">
            Understanding your decision before stress-testing it.
          </p>
        </div>
        <span className="numeric text-small font-medium text-ink-muted">
          {String(Math.min(turnNumber, maxTurns)).padStart(2, '0')} / {String(maxTurns).padStart(2, '0')}
        </span>
      </div>

      <div className="grid gap-0 md:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="flex min-h-[22rem] flex-col">
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-5 py-5 md:px-6">
            {interview.messages.map((message) => (
              <ConversationBubble key={message.id} message={message} />
            ))}

            {!interview.agentAvailable ? (
              <div className="flex items-start gap-2 rounded-lg border border-warning-line bg-panel-warning px-3.5 py-2.5 text-small text-warning-ink">
                <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                REGRET couldn't continue the interview, but you can continue with the information
                you've already provided.
              </div>
            ) : null}

            {interview.error ? (
              <div className="flex items-start gap-2 rounded-lg border border-danger-line bg-panel-danger px-3.5 py-2.5 text-small text-danger-ink">
                <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                {interview.error.message}
              </div>
            ) : null}

            {isDone ? (
              <div className="rounded-lg border border-accent-line bg-panel-accent px-3.5 py-3 text-small text-accent-ink">
                <Badge tone={READINESS_TONE[interview.readiness ?? 'early']} size="sm" dot>
                  {READINESS_LABEL[interview.readiness ?? 'early']}
                </Badge>
              </div>
            ) : null}
          </div>

          {!isDone && interview.suggestedChips.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 border-t border-hairline px-5 py-3 md:px-6">
              {interview.suggestedChips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => pickChip(chip)}
                  disabled={isSubmitting}
                  className="rounded-full border border-hairline bg-surface-inset px-3 py-1 text-micro font-medium text-ink-secondary transition-colors duration-150 hover:border-hairline-strong hover:bg-surface-raised disabled:opacity-50"
                >
                  {chip}
                </button>
              ))}
            </div>
          ) : null}

          {!isDone ? (
            <form onSubmit={submit} className="flex items-end gap-2 border-t border-hairline px-5 py-4 md:px-6">
              <textarea
                aria-label="Your answer"
                rows={1}
                value={draft}
                disabled={isSubmitting}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    submit(event as unknown as FormEvent<HTMLFormElement>);
                  }
                }}
                placeholder="Type your answer…"
                className="max-h-32 min-h-9.5 flex-1 resize-none rounded-md border border-hairline bg-surface-inset px-3 py-2 text-small text-ink placeholder:text-ink-muted transition-colors focus:border-accent focus:bg-surface disabled:opacity-50"
              />
              <Button type="submit" size="md" disabled={!draft.trim() || isSubmitting} loading={isSubmitting}>
                Send
              </Button>
            </form>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline px-5 py-3 md:px-6">
            <Button variant="ghost" size="sm" onClick={onSkip} disabled={isDone && interview.stage !== 'ready'}>
              Skip to stress test
            </Button>
            {isDone ? (
              <Button
                variant="primary"
                size="sm"
                rightIcon={ArrowRight}
                loading={interview.stage === 'completing'}
                onClick={onContinueToStressTest}
              >
                Stress Test This Decision
              </Button>
            ) : null}
          </div>
        </div>

        <DecisionModelPanel interview={interview} />
      </div>
    </div>
  );
}

function ConversationBubble({ message }: { message: InterviewMessage }) {
  const isUser = message.role === 'user';
  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <p
        className={cn(
          'max-w-[85%] rounded-lg px-3.5 py-2.5 text-small leading-relaxed',
          isUser ? 'bg-panel-accent text-accent-ink' : 'bg-surface-inset text-ink',
        )}
      >
        {message.text}
      </p>
    </div>
  );
}

function DecisionModelPanel({ interview }: { interview: InterviewState }) {
  const state = interview.state;
  return (
    <div className="border-t border-hairline px-5 py-5 md:border-t-0 md:border-l md:px-5">
      <p className="eyebrow">Decision model</p>

      <ModelSection title="Goal">
        {state?.desired_outcome ? (
          <p className="text-small text-ink-secondary">{state.desired_outcome}</p>
        ) : (
          <EmptyModelHint />
        )}
      </ModelSection>

      <ModelSection title="Known">
        <ModelList items={[...(state?.constraints ?? []), ...(state?.commitments ?? [])]} mark="✓" />
      </ModelSection>

      <ModelSection title="Assumptions">
        <ModelList items={[...(state?.beliefs ?? []), ...(state?.discovered_assumptions ?? [])]} mark="?" />
      </ModelSection>

      <ModelSection title="Uncertainties">
        <ModelList items={[...(state?.uncertainties ?? []), ...(state?.discovered_unknowns ?? [])]} mark="?" />
      </ModelSection>

      <ModelSection title="Alternatives">
        <ModelList items={state?.alternatives ?? []} mark="·" />
      </ModelSection>
    </div>
  );
}

function ModelSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mt-4 first:mt-3">
      <p className="text-micro font-medium tracking-[0.08em] text-ink-muted uppercase">{title}</p>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function ModelList({ items, mark }: { items: string[]; mark: string }) {
  if (items.length === 0) return <EmptyModelHint />;
  return (
    <ul className="space-y-1">
      {items.slice(0, 4).map((item) => (
        <li key={item} className="flex items-start gap-1.5 text-small text-ink-secondary">
          <span className="mt-0.5 text-ink-muted" aria-hidden>
            {mark}
          </span>
          <span className="min-w-0">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function EmptyModelHint() {
  return <p className="text-micro text-ink-muted">Not yet discussed.</p>;
}
