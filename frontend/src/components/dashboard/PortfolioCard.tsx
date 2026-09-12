import { useMemo } from 'react';
import { useReducedMotion } from 'framer-motion';
import { ChartPie } from 'lucide-react';
import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { PortfolioBand } from '@/lib/buildDashboard';
import { cn } from '@/lib/cn';
import { toneFill, toneHex } from '@/lib/tone';

export interface PortfolioCardProps {
  bands: PortfolioBand[];
}

/**
 * Status composition of the decisions in this workspace. A plain ring plus
 * a readable legend - real counts derived from `GET /decisions`, no
 * fabricated risk score (the backend does not compute one on the decision
 * itself).
 */
export function PortfolioCard({ bands }: PortfolioCardProps) {
  const reduceMotion = useReducedMotion();

  const { slices, total } = useMemo(() => {
    const sum = bands.reduce((acc, band) => acc + band.count, 0);
    return {
      total: sum,
      slices: bands.map((band) => ({
        name: band.label,
        value: band.count,
        fill: toneHex[band.tone],
      })),
    };
  }, [bands]);

  return (
    <Card className="flex h-full min-w-0 flex-col overflow-hidden">
      <div className="min-w-0">
        <CardTitle>Decision portfolio</CardTitle>
        <p className="mt-0.5 break-words text-small text-ink-muted">Status spread across your decisions</p>
      </div>

      {total === 0 ? (
        <EmptyState
          size="inline"
          icon={ChartPie}
          title="Nothing to show yet"
          description="Create a decision to see its status here."
        />
      ) : (
        <div className="mt-5 flex min-w-0 flex-1 flex-col items-center gap-5 2xl:flex-row 2xl:gap-7">
          <div className="relative aspect-square w-full max-w-36 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={slices}
                  dataKey="value"
                  nameKey="name"
                  innerRadius="68%"
                  outerRadius="100%"
                  startAngle={90}
                  endAngle={-270}
                  paddingAngle={3}
                  stroke="none"
                  isAnimationActive={!reduceMotion}
                  animationDuration={600}
                >
                  {slices.map((slice) => (
                    <Cell key={slice.name} fill={slice.fill} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="numeric text-metric text-ink">{total}</span>
              <span className="text-micro text-ink-muted">total</span>
            </div>
          </div>

          <ul className="w-full min-w-0 space-y-3">
            {bands.map((band) => {
              const share = Math.round((band.count / total) * 100);

              return (
                <li
                  key={band.label}
                  className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)_auto_auto] items-center gap-x-2 sm:gap-x-3"
                >
                  <span className={cn('size-2 shrink-0 rounded-full', toneFill[band.tone])} aria-hidden />
                  <span className="min-w-0 break-words text-small text-ink-secondary">{band.label}</span>
                  <span className="numeric text-small font-medium text-ink">{band.count}</span>
                  <span className="numeric w-9 text-right text-small text-ink-muted">{share}%</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Card>
  );
}
