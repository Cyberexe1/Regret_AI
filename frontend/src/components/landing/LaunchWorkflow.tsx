import { useCallback, useId, useRef, useState, type KeyboardEvent } from 'react';
import { Reveal } from '@/components/Reveal';
import { LAUNCH_ANCHORS, workflowHeading, workflowLead, workflowTabs } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { MockFrame } from './MockScreen';
import { BAND, GRADIENT_TEXT, TILE, TILE_LINE, TYPE_LEAD, TYPE_SECTION } from './tokens';

/**
 * Reference tabs band: a vertical list of tab cards on the left, the matching
 * product mockup panelled on the right.
 *
 * Implemented as a real tablist — arrow keys move between tabs, the selected
 * tab owns focus, and the panel is wired with `aria-labelledby` — because the
 * reference is a static mock and does not answer how it behaves for keyboard
 * users.
 */
export function LaunchWorkflow() {
  const [active, setActive] = useState(0);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const baseId = useId();

  const tabId = (index: number) => `${baseId}-tab-${index}`;
  const panelId = (index: number) => `${baseId}-panel-${index}`;

  /**
   * Roving tabindex: only the selected tab is in the Tab order, so keyboard
   * selection has to carry focus with it. Without this the previously focused
   * tab becomes `tabIndex={-1}` and focus falls back to the document body,
   * stranding the user after a single arrow press.
   */
  const selectAndFocus = useCallback((index: number) => {
    const next = (index + workflowTabs.length) % workflowTabs.length;
    setActive(next);
    tabRefs.current[next]?.focus();
  }, []);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const keys: Record<string, number | undefined> = {
      ArrowDown: active + 1,
      ArrowRight: active + 1,
      ArrowUp: active - 1,
      ArrowLeft: active - 1,
      Home: 0,
      End: workflowTabs.length - 1,
    };

    const next = keys[event.key];
    if (next === undefined) return;

    event.preventDefault();
    selectAndFocus(next);
  };

  return (
    <section
      id={LAUNCH_ANCHORS.howItWorks}
      className={cn(BAND, 'scroll-mt-24 pt-8 pb-16 md:pt-10 md:pb-20')}
    >
      <Reveal className="flex min-w-0 flex-col items-center gap-8">
        <h2 className={cn(TYPE_SECTION, GRADIENT_TEXT, 'max-w-4xl text-center')}>
          {workflowHeading}
        </h2>
        <p className={cn(TYPE_LEAD, 'max-w-2xl text-center')}>{workflowLead}</p>
      </Reveal>

      <div className="mt-12 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4 sm:mt-16 lg:grid-cols-[minmax(0,23rem)_minmax(0,1fr)]">
        <div
          role="tablist"
          aria-label="Workflow stages"
          aria-orientation="vertical"
          className="flex min-w-0 flex-col gap-3"
          onKeyDown={onKeyDown}
        >
          {workflowTabs.map(({ icon: Icon, title, body }, index) => {
            const selected = index === active;

            return (
              <button
                key={title}
                ref={(node) => {
                  tabRefs.current[index] = node;
                }}
                type="button"
                role="tab"
                id={tabId(index)}
                aria-selected={selected}
                aria-controls={panelId(index)}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActive(index)}
                className={cn(
                  'flex w-full min-w-0 gap-2 rounded-md py-3 pr-4 pl-3 text-left transition-colors duration-150 ease-out sm:pr-5',
                  selected
                    ? 'bg-gradient-to-t from-white/5 to-white/10'
                    : 'hover:bg-white/[0.04]',
                )}
              >
                <span className="shrink-0 p-0.5">
                  <Icon
                    className={cn('size-4', selected ? 'text-ink' : 'text-ink-secondary')}
                    aria-hidden
                  />
                </span>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span
                    className={cn(
                      'text-small font-semibold',
                      selected ? 'text-ink' : 'text-ink-secondary',
                    )}
                  >
                    {title}
                  </span>
                  <span className="mt-0.5 text-xs leading-relaxed text-ink-secondary">{body}</span>
                </span>
              </button>
            );
          })}
        </div>

        {workflowTabs.map((tab, index) => (
          <div
            key={tab.title}
            role="tabpanel"
            id={panelId(index)}
            aria-labelledby={tabId(index)}
            hidden={index !== active}
            className={cn(TILE, TILE_LINE, 'min-w-0 overflow-hidden p-3 sm:p-8')}
          >
            <MockFrame
              variant={tab.mockup}
              className="h-[18rem] min-w-0 max-w-full sm:h-[28rem] lg:h-[30rem]"
            />
          </div>
        ))}
      </div>
    </section>
  );
}
