import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Card, CardTitle } from '@/components/ui/Card';
import { analysisAgents, type AnalysisFinding } from '@/data/analysisAgents';
import { cn } from '@/lib/cn';
import { toneFill, toneText } from '@/lib/tone';

const agentNameById = new Map(analysisAgents.map((agent) => [agent.id, agent.name]));

export interface LiveFindingsProps {
  findings: AnalysisFinding[];
  isComplete: boolean;
}

/**
 * Conclusions as they are released. Each entry is a result attributed to a
 * specialist, never a trace of how it got there.
 */
export function LiveFindings({ findings, isComplete }: LiveFindingsProps) {
  const reduceMotion = useReducedMotion();

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-hairline px-5 py-4 md:px-6">
        <div>
          <CardTitle>Live findings</CardTitle>
          <p className="mt-0.5 text-small text-ink-muted">
            {isComplete
              ? `${findings.length} findings recorded`
              : 'Released as each specialist reports'}
          </p>
        </div>
        <span className="numeric text-small text-ink-muted">{findings.length}</span>
      </div>

      <div className="px-5 py-5 md:px-6">
        {findings.length === 0 ? (
          <p className="py-4 text-small text-ink-muted">Waiting on the first specialist.</p>
        ) : (
          <ul className="space-y-3">
            <AnimatePresence initial={false}>
              {findings.map((finding) => (
                <motion.li
                  key={finding.id}
                  layout={!reduceMotion}
                  initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
                  animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                  transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
                  className="flex gap-3 rounded-lg border border-hairline bg-surface-raised px-4 py-3"
                >
                  <span
                    className={cn('mt-1.5 size-2 shrink-0 rounded-full', toneFill[finding.tone])}
                    aria-hidden
                  />
                  <div className="min-w-0">
                    <p className="text-small text-ink">{finding.headline}</p>
                    <p className={cn('mt-1 text-micro', toneText[finding.tone])}>
                      {agentNameById.get(finding.agentId) ?? 'Engine'}
                    </p>
                  </div>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </Card>
  );
}
