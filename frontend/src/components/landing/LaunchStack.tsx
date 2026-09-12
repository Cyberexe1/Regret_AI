import { Reveal } from '@/components/Reveal';
import { stack, stackHeading } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { BAND } from './tokens';

/** Logo strip: one centred label, then icon + name + version pairs. */
export function LaunchStack() {
  return (
    <section className={cn(BAND, 'py-16 md:py-20')}>
      <Reveal className="flex flex-col items-center gap-12">
        <p className="text-small font-semibold text-ink">{stackHeading}</p>

        <ul className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6">
          {stack.map(({ icon: Icon, name, version }) => (
            <li key={name} className="flex items-center gap-2">
              <Icon className="size-6 text-ink" aria-hidden />
              <span className="text-small font-medium text-ink">{name}</span>
              {version ? <span className="text-small text-ink-secondary">{version}</span> : null}
            </li>
          ))}
        </ul>
      </Reveal>
    </section>
  );
}
