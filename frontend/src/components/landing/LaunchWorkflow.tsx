import { useId, useState } from 'react';
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
  const baseId = useId();

  const tabId = (index: number) => `${baseId}-tab-${index}`;
  const panelId = (index: number) => `${baseId}-panel-${index}`;

  const move = (delta: number) => {
    setActive((current) => (current + delta + workflowTabs.length) % workflowTabs.length);
  };

  return (
    <section
      id={LAUNCH_ANCHORS.howItWorks}
      className={cn(BAND, 'scroll-mt-24 pt-8 pb-16 md:pt-10 md:pb-20')}
    >
      <Reveal className="flex flex-col items-center gap-8">
        <h2 className={cn(TYPE_SECTION, GRADIENT_TEXT, 'max-w-4xl text-center')}>
          {workflowHeading}
        </h2>
        <p className={cn(TYPE_LEAD, 'max-w-2xl text-center')}>{workflowLead}</p>
      </Reveal>

      <div className="mt-16 grid gap-4 lg:grid-cols-[minmax(0,23rem)_minmax(0,1fr)]">
        <div
          role="tablist"
          aria-label="Workflow stages"
          aria-orientation="vertical"
          className="flex flex-col gap-3"
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
              event.preventDefault();
              move(1);
            } else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
              event.preventDefault();
              move(-1);
            }
          }}
        >
          {workflowTabs.map(({ icon: Icon, title, body }, index) => {
            const selected = index === active;

            return (
              <button
                key={title}
                type="button"
                role="tab"
                id={tabId(index)}
                aria-selected={selected}
                aria-controls={panelId(index)}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActive(index)}
                className={cn(
                  'flex gap-2 rounded-md py-3 pr-5 pl-3 text-left transition-colors duration-150 ease-out',
                  selected
                    ? 'bg-gradient-to-t from-white/5 to-white/10'
                    : 'hover:bg-white/[0.04]',
                )}
              >
                <span className="p-0.5">
                  <Icon
                    className={cn('size-4', selected ? 'text-ink' : 'text-ink-secondary')}
                    aria-hidden
                  />
                </span>
                <span className="flex flex-col">
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
            className={cn(TILE, TILE_LINE, 'p-4 sm:p-8')}
          >
            <MockFrame variant={tab.mockup} className="h-[22rem] sm:h-[28rem] lg:h-[30rem]" />
          </div>
        ))}
      </div>
    </section>
  );
}
