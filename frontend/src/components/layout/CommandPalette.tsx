import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { CornerDownLeft, ScanSearch, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Kbd } from '@/components/ui/Kbd';
import { primaryNav, ROUTES } from '@/data/navigation';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { useLockBodyScroll } from '@/hooks/useLockBodyScroll';
import { cn } from '@/lib/cn';
import type { NavItem } from '@/types';

/** Everywhere the palette can take you. Navigation only, for now. */
const destinations: NavItem[] = [
  ...primaryNav,
  { label: 'Analysis Workspace', to: ROUTES.analysis, icon: ScanSearch },
];

export interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Command palette placeholder. It navigates between the real routes of the
 * shell; searching decisions and experiments arrives with the analysis engine.
 */
export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);

  useEscapeKey(open, onClose);
  useLockBodyScroll(open);

  // Every opening starts from a clean slate with the input focused.
  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActiveIndex(0);
    const frame = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [open]);

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return destinations;
    return destinations.filter((item) => item.label.toLowerCase().includes(needle));
  }, [query]);

  // Keep the highlight inside the result list as it shrinks.
  useEffect(() => {
    setActiveIndex((index) => (index >= results.length ? 0 : index));
  }, [results.length]);

  const go = (to: string) => {
    onClose();
    navigate(to);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (results.length === 0 ? 0 : (index + 1) % results.length));
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) =>
        results.length === 0 ? 0 : (index - 1 + results.length) % results.length,
      );
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      const target = results[activeIndex];
      if (target) go(target.to);
    }
  };

  return createPortal(
    <AnimatePresence>
      {open ? (
        <div className="fixed inset-0 z-60 flex items-start justify-center px-4 pt-[12vh]">
          <motion.div
            className="absolute inset-0 bg-canvas/80 backdrop-blur-sm"
            initial={reduceMotion ? undefined : { opacity: 0 }}
            animate={reduceMotion ? undefined : { opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
          />

          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            className="relative z-10 w-full max-w-xl overflow-hidden rounded-2xl border border-hairline-strong bg-surface-overlay shadow-overlay"
            initial={reduceMotion ? undefined : { opacity: 0, y: -8, scale: 0.985 }}
            animate={reduceMotion ? undefined : { opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -6, scale: 0.985 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="flex items-center gap-3 border-b border-hairline px-4">
              <Search className="size-4 shrink-0 text-ink-muted" aria-hidden />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Jump to a page"
                aria-label="Search commands"
                className="h-13 flex-1 bg-transparent text-body text-ink outline-none placeholder:text-ink-faint"
              />
              <Kbd>Esc</Kbd>
            </div>

            <div className="max-h-80 overflow-y-auto p-2">
              {results.length === 0 ? (
                <p className="px-3 py-6 text-center text-small text-ink-muted">
                  No page matches &ldquo;{query.trim()}&rdquo;
                </p>
              ) : (
                <>
                  <p className="eyebrow px-3 pt-2 pb-1.5">Navigate</p>
                  <ul>
                    {results.map((item, index) => {
                      const Icon = item.icon;
                      const isActive = index === activeIndex;

                      return (
                        <li key={item.to}>
                          <button
                            type="button"
                            onClick={() => go(item.to)}
                            onMouseEnter={() => setActiveIndex(index)}
                            className={cn(
                              'flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-small transition-colors',
                              isActive
                                ? 'bg-accent-soft text-ink'
                                : 'text-ink-secondary hover:bg-surface-raised',
                            )}
                          >
                            <Icon
                              className={cn(
                                'size-4 shrink-0',
                                isActive ? 'text-accent-ink' : 'text-ink-muted',
                              )}
                              aria-hidden
                            />
                            <span className="truncate">{item.label}</span>
                            {isActive ? (
                              <CornerDownLeft
                                className="ml-auto size-3.5 shrink-0 text-ink-muted"
                                aria-hidden
                              />
                            ) : null}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-hairline bg-surface-raised/60 px-4 py-3">
              <span className="flex items-center gap-1.5 text-micro text-ink-muted">
                <Kbd>↑</Kbd>
                <Kbd>↓</Kbd>
                to move
              </span>
              <span className="flex items-center gap-1.5 text-micro text-ink-muted">
                <Kbd>↵</Kbd>
                to open
              </span>
              <span className="ml-auto text-micro text-ink-faint">
                Decision search arrives with the analysis engine
              </span>
            </div>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
