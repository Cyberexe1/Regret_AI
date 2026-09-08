export interface ChartTooltipItem {
  name?: string;
  value?: number | string;
  color?: string;
  dataKey?: string | number;
}

export interface ChartTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: ChartTooltipItem[];
  /** Appended to every value, e.g. "/100". */
  valueSuffix?: string;
  /** Overrides rendering of each value, e.g. for currency. */
  formatValue?: (value: number | string | undefined) => string;
  /** Overrides rendering of the axis label. */
  formatLabel?: (label: string | number) => string;
}

/**
 * Dark tooltip surface for Recharts. Pass as `<Tooltip content={<ChartTooltip />} />`.
 */
export function ChartTooltip({
  active,
  label,
  payload,
  valueSuffix = '',
  formatValue,
  formatLabel,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-md border border-hairline-strong bg-surface-overlay px-3 py-2 shadow-overlay">
      {label !== undefined ? (
        <p className="mb-1.5 text-micro tracking-wide text-ink-muted uppercase">
          {formatLabel ? formatLabel(label) : label}
        </p>
      ) : null}
      <ul className="space-y-1">
        {payload.map((item, index) => (
          <li key={item.dataKey ?? index} className="flex items-center gap-2 text-small">
            <span
              className="size-2 shrink-0 rounded-sm"
              style={{ backgroundColor: item.color }}
              aria-hidden
            />
            <span className="text-ink-secondary">{item.name}</span>
            <span className="numeric ml-auto font-medium text-ink">
              {formatValue ? formatValue(item.value) : `${item.value}${valueSuffix}`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
