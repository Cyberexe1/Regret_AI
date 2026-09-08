import { useMemo } from 'react';
import { useReducedMotion } from 'framer-motion';
import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';
import { Card, CardTitle } from '@/components/ui/Card';
import { portfolioBands } from '@/data/dashboard';
import { cn } from '@/lib/cn';
import { toneFill, toneHex, riskTone } from '@/lib/tone';

/**
 * Risk composition of the analysed portfolio. A plain ring plus a readable
 * legend: no axes, no tooltip, no trading-desk chrome.
 */
export function PortfolioCard() {
  const reduceMotion = useReducedMotion();

  const { slices, total } = useMemo(() => {
    const sum = portfolioBands.reduce((acc, band) => acc + band.count, 0);
    return {
      total: sum,
      slices: portfolioBands.map((band) => ({
        name: band.label,
        value: band.count,
        fill: toneHex[riskTone[band.risk]],
      })),
    };
  }, []);

  return (
    <Card className="flex h-full flex-col">
      <div>
        <CardTitle>Decision portfolio</CardTitle>
        <p className="mt-0.5 text-small text-ink-muted">Risk spread across analysed decisions</p>
      </div>

      <div className="mt-5 flex flex-1 flex-col items-center gap-6 sm:flex-row sm:gap-7">
        <div className="relative size-38 shrink-0">
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
            <span className="text-micro text-ink-muted">analysed</span>
          </div>
        </div>

        <ul className="w-full space-y-3">
          {portfolioBands.map((band) => {
            const share = Math.round((band.count / total) * 100);

            return (
              <li key={band.risk} className="flex items-center gap-3">
                <span
                  className={cn('size-2 shrink-0 rounded-full', toneFill[riskTone[band.risk]])}
                  aria-hidden
                />
                <span className="flex-1 text-small text-ink-secondary">{band.label}</span>
                <span className="numeric text-small font-medium text-ink">{band.count}</span>
                <span className="numeric w-9 text-right text-small text-ink-muted">{share}%</span>
              </li>
            );
          })}
        </ul>
      </div>
    </Card>
  );
}
